import os
import psycopg2
from psycopg2 import sql
import pandas as pd
import re
import html
import json
import ast

CONN = None

def init_cursor():
    """ initializes a connection to the database """
    global CONN
    if CONN == None:
        CONN = psycopg2.connect(
                host="postgis_container",
                database="haix",
                user="postgres",
                password="secret"
            )
    cur = CONN.cursor()
    return cur

def open_table(schema, table, col_list, filter=None, order_by='idx'):
    """ selects columns from a db table, optional filtering by condition """
    if filter is not None:
        print(len(filter[1]))
    with init_cursor() as haix:
        col_names = sql.SQL(', ').join(sql.Identifier(n) for n in col_list)
        if filter is None:
            query = sql.SQL("SELECT {} " + 
                            "FROM {} " +
                            "ORDER BY {} ASC").format(
                                col_names,
                                sql.Identifier(schema, table),
                                sql.Identifier(order_by)
                            )
            print(haix.mogrify(query))
            haix.execute(query)
        elif len(filter) == 2 and filter[0] in col_list:
            query = sql.SQL("SELECT {} " +
                            "FROM {} " +
                            "WHERE {} IN %s " +
                            "ORDER BY {} ASC").format(
                                col_names,
                                sql.Identifier(schema, table),
                                sql.Identifier(filter[0]),
                                sql.Identifier('idx') 
                            )
            print(haix.mogrify(query, (filter[1],)))
            haix.execute(query, (filter[1],))
        else:
            return "Filter is incorrectly formatted"
        results = haix.fetchall()
        df = pd.DataFrame.from_records(results, columns = col_list)
        return df

def convert_to_geostr(type, coordinate):
    """ formats type and coordinates to valid postgis geometry string """
    coords = ','.join([str(c[0]) + " " + str(c[1]) for c in coordinate])
    return "{}(({}))".format(type, coords)

def convert_to_geojson_file(schema, table, outfile_path):
    """ pulls data from geometry table and writes it to a geojson file """
    with init_cursor() as haix:
        query = sql.SQL("SELECT jsonb_build_object(" +
                            "'type', 'FeatureCollection', " +
                            "'features', jsonb_agg(features.feature)" +
                        ") FROM (" +
                            "SELECT json_build_object(" +
                                "'type', 'Feature', " +
                                "'geometry', ST_AsGeoJSON(geom)::json, " +
                                "'id', {}" +
                            ") AS feature " +
                        "FROM (SELECT * FROM {}) geo) features;").format(
                            sql.Identifier('idx'),
                            sql.Identifier(schema, table)
                    )
        print(haix.mogrify(query))
        haix.execute(query)
        results = haix.fetchall()

        with open(outfile_path, "w") as outfile:
            json.dump(results[0][0], outfile)

def add_row(schema, table, values: dict):
    """ insert a row into a table in the database """
    global CONN
    with init_cursor() as haix:
        col_names = sql.SQL(', ').join(sql.Identifier(n) for n in values.keys())

        parameters = sql.SQL(', ').join(sql.Placeholder() * len(values.values()))

        query = sql.SQL("INSERT INTO {} ({}) " +
                        "VALUES ({});").format(
                            sql.Identifier(schema, table),
                            col_names,
                            parameters
                        )
        values = tuple([j for j in values.values()])
        print(haix.mogrify(query, values))
        haix.execute(query, values)
        CONN.commit()

def clean(input):
    """ clean user input before adding it to a table """
    to_remove = re.compile(r"['*`~@#$%^&*()_+={}\\|/<>;]")
    if input is not None:
        # strip input of special characters
        input = to_remove.sub('', input)
        # strip input of html scripts
        input = html.escape(input)
    return input

def get_max_id(schema, table):
    """ return the highest id value from a table """
    with init_cursor() as haix:
        if table is "path":
            query = sql.SQL("SELECT MAX(path_id) "
                            "FROM {};").format(
                sql.Identifier(schema, table)
            )
        else:
            query = sql.SQL("SELECT MAX(idx) "
                            "FROM {};").format(
                            sql.Identifier(schema, table)
                        )

        print(haix.mogrify(query))
        haix.execute(query)
        results = haix.fetchall()

        return int(results[0][0])


def select_distinct(schema, table, col):
    """ return a set of values from a column in a table """
    with init_cursor() as haix:
        query = sql.SQL("SELECT DISTINCT {} " +
                        "FROM {};").format(
                            sql.Identifier(col),
                            sql.Identifier(schema, table)
                        )
        print(haix.mogrify(query))
        haix.execute(query)
        results = haix.fetchall()
        return results
    
def delete_row(schema, table, filter):
    """ remove a row from a table in the database """
    global CONN
    with init_cursor() as haix:
        if len(filter) == 2:
            query = sql.SQL("DELETE " +
                            "FROM {} " +
                            "WHERE {} = %s").format(
                                sql.Identifier(schema, table),
                                sql.Identifier(filter[0]) 
                            )
            print(haix.mogrify(query, ((filter[1],))))
            haix.execute(query, ((filter[1],)))
            CONN.commit()
            return "Deleted successfully"
        else:
            return "Error while deleting"
        
def update_table(schema, table, values, filter):
    """ update the values of a table where a condition is met """
    global CONN
    with init_cursor() as haix:
        if len(filter) == 2 and len(values) > 0:
            set_values = sql.SQL(', ').join(
                sql.Composed([sql.Identifier(k), sql.SQL(" = "), sql.Placeholder()]) for k in values.keys()
            )
            query = sql.SQL("UPDATE {} " +
                            "SET {} " +
                            "WHERE {} = %s").format(
                                sql.Identifier(schema, table),
                                set_values,
                                sql.Identifier(filter[0])
                            )
            values.update(id=filter[1])
            values = tuple(values.values())
            print(haix.mogrify(query, values))
            haix.execute(query, values)
            CONN.commit()
            return "Updated successfully"
        else:
            return "Error while updating"