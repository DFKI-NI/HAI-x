import os
import psycopg2
from psycopg2 import sql, extensions
import pandas as pd
import re
import html
import json
import ast
import logging

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
    # Roll back any previously failed transaction so the connection is usable
    if CONN.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
        try:
            CONN.rollback()
        except Exception:
            pass
    cur = CONN.cursor()
    return cur

def _get_existing_columns(schema, table):
    """Return the set of column names that actually exist in the given table."""
    with init_cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s",
            (schema, table)
        )
        return {row[0] for row in cur.fetchall()}

def open_table(schema, table, col_list, filter=None, order_by='idx'):
    """ selects columns from a db table, optional filtering by condition """
    if filter is not None:
        print(len(filter[1]))

    # Only request columns that actually exist in the database table
    try:
        existing = _get_existing_columns(schema, table)
        effective_cols = [c for c in col_list if c in existing]
        if not effective_cols:
            effective_cols = col_list  # fallback: let the DB raise the error
    except Exception:
        effective_cols = col_list

    with init_cursor() as haix:
        col_names = sql.SQL(', ').join(sql.Identifier(n) for n in effective_cols)
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
        df = pd.DataFrame.from_records(results, columns = effective_cols)
        # Add missing columns (from col_list but not in DB) as NaN
        for col in col_list:
            if col not in df.columns:
                df[col] = None
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

    # Only insert into columns that actually exist in the database table
    try:
        existing = _get_existing_columns(schema, table)
        filtered_values = {k: v for k, v in values.items() if k in existing}
        if not filtered_values:
            filtered_values = values  # fallback: let the DB raise the error
    except Exception:
        filtered_values = values

    with init_cursor() as haix:
        col_names = sql.SQL(', ').join(sql.Identifier(n) for n in filtered_values.keys())

        parameters = sql.SQL(', ').join(sql.Placeholder() * len(filtered_values.values()))

        query = sql.SQL("INSERT INTO {} ({}) " +
                        "VALUES ({});").format(
                            sql.Identifier(schema, table),
                            col_names,
                            parameters
                        )
        values = tuple([j for j in filtered_values.values()])
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

        if results[0][0] is None:
            result = 0
        else:
            result = int(results[0][0])

        return result


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

def select_distinct_filtered(schema, table, col, filter_col, filter_val):
    """ return distinct values of col from table where filter_col = filter_val """
    with init_cursor() as haix:
        query = sql.SQL("SELECT DISTINCT {} FROM {} WHERE {} = %s ORDER BY {} ASC;").format(
            sql.Identifier(col),
            sql.Identifier(schema, table),
            sql.Identifier(filter_col),
            sql.Identifier(col)
        )
        haix.execute(query, (filter_val,))
        results = haix.fetchall()
        return [r[0] for r in results]

def get_lakes_with_apa(schema, bathymetry_table, apa_table):
    """ return lake names that exist in both bathymetry and apa_index tables """
    with init_cursor() as haix:
        query = sql.SQL(
            "SELECT DISTINCT b.{col} FROM {bath} b "
            "INNER JOIN (SELECT DISTINCT {col} FROM {apa}) a ON b.{col} = a.{col} "
            "ORDER BY b.{col} ASC;"
        ).format(
            col=sql.Identifier('lake_name'),
            bath=sql.Identifier(schema, bathymetry_table),
            apa=sql.Identifier(schema, apa_table),
        )
        haix.execute(query)
        results = haix.fetchall()
        return [r[0] for r in results]
    
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

def delete_rows_by_lake(schema, table, lake_name):
    """ delete all rows from table where lake_name matches """
    global CONN
    with init_cursor() as haix:
        query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
            sql.Identifier(schema, table),
            sql.Identifier('lake_name')
        )
        print(haix.mogrify(query, (lake_name,)))
        haix.execute(query, (lake_name,))
        CONN.commit()
        return "Deleted successfully"

def delete_rows_by_lake_date(schema, table, lake_name, date_val):
    """ delete all rows from table where lake_name and date match """
    global CONN
    with init_cursor() as haix:
        query = sql.SQL("DELETE FROM {} WHERE {} = %s AND {} = %s").format(
            sql.Identifier(schema, table),
            sql.Identifier('lake_name'),
            sql.Identifier('date')
        )
        print(haix.mogrify(query, (lake_name, date_val)))
        haix.execute(query, (lake_name, date_val))
        CONN.commit()
        return "Deleted successfully"
        
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