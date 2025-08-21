-- PostgreSQL v17.2
-- pgAdmin 4 v8.14
-- PostGIS extension
-- USER = 'postgres'
-- PASS = '****'

-- create database and schema

CREATE DATABASE haix
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LOCALE_PROVIDER = 'libc'
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

\c haix

CREATE SCHEMA interface
    AUTHORIZATION postgres;

CREATE EXTENSION postgis;

-- set up area table - create table, import data from csv, and check that data is properly imported

CREATE TABLE IF NOT EXISTS interface.area
(
    idx integer NOT NULL,
    type text COLLATE pg_catalog."default",
    date date,
    description text COLLATE pg_catalog."default",
    image_path text COLLATE pg_catalog."default",
    CONSTRAINT area_pkey PRIMARY KEY (idx)
);

COPY interface.area(idx, type, date, description, image_path)
FROM '/docker-entrypoint-initdb.d/area.csv'
DELIMITER ','
CSV HEADER;

SELECT * FROM interface.area
ORDER BY idx ASC;

-- set up geo table

CREATE TABLE IF NOT EXISTS interface.geo
(
    idx integer NOT NULL,
    geom text COLLATE pg_catalog."default",
    CONSTRAINT geom_pkey PRIMARY KEY (idx),
    CONSTRAINT f_idx FOREIGN KEY (idx)
        REFERENCES interface.area (idx) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE CASCADE
        NOT VALID
);

COPY interface.geo(idx, geom)
FROM '/docker-entrypoint-initdb.d/geo.csv'
DELIMITER ','
CSV HEADER;

SELECT * FROM interface.geo
ORDER BY idx ASC;

-- set up path table

CREATE TABLE IF NOT EXISTS interface.path
(
    path_id integer NOT NULL,
    lat numeric,
    lon numeric,
    date date,
    idx text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT path_pkey PRIMARY KEY (idx)
);

COPY interface.path(path_id, lat, lon, date, idx)
FROM '/docker-entrypoint-initdb.d/path.csv'
DELIMITER ','
CSV HEADER;

SELECT * FROM interface.path
ORDER BY idx ASC;

-- set up trajectory table

CREATE TABLE IF NOT EXISTS interface.trajectory
(
    "timestamp" bigint,
    latitude numeric,
    longitude numeric,
    date date,
    mowed_grass integer,
    idx bigint NOT NULL,
    CONSTRAINT trajectory_pkey PRIMARY KEY (idx)
);

COPY interface.trajectory(timestamp, latitude, longitude, date, mowed_grass, idx)
FROM '/docker-entrypoint-initdb.d/trajectory.csv'
DELIMITER ','
CSV HEADER;

SELECT * FROM interface.trajectory
ORDER BY idx ASC;