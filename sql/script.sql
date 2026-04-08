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



CREATE TABLE IF NOT EXISTS interface.evaluation
(
    id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    lat1 NUMERIC,
    lon1 NUMERIC,
    lat2 NUMERIC,
    lon2 NUMERIC,
    weeding NUMERIC
);

-- set up area table - create table, import data from csv, and check that data is properly imported
CREATE TABLE IF NOT EXISTS interface.area
(
    idx integer NOT NULL,
    type text COLLATE pg_catalog."default",
    date date,
    description text COLLATE pg_catalog."default",
    image_path text COLLATE pg_catalog."default",
    is_capacitated boolean DEFAULT FALSE,
    lake_name text COLLATE pg_catalog."default",
    cluster_id integer,
    cluster_total_volume NUMERIC,
    harvester_capacity NUMERIC,
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

-- set up bathymetry table

CREATE TABLE IF NOT EXISTS interface.bathymetry
(
    idx SERIAL PRIMARY KEY,
    lake_name text COLLATE pg_catalog."default",
    date date,
    lat NUMERIC,
    lon NUMERIC,
    depth NUMERIC,
    description text COLLATE pg_catalog."default"
);

-- set up APA index table

CREATE TABLE IF NOT EXISTS interface.apa_index
(
    idx SERIAL PRIMARY KEY,
    lake_name text COLLATE pg_catalog."default",
    date date,
    lat NUMERIC,
    lon NUMERIC,
    apa_value NUMERIC,
    description text COLLATE pg_catalog."default"
);

-- set up plant volume table

CREATE TABLE IF NOT EXISTS interface.plant_volume
(
    idx SERIAL PRIMARY KEY,
    lake_name text COLLATE pg_catalog."default",
    date date,
    lat NUMERIC,
    lon NUMERIC,
    volume NUMERIC,
    apa_value NUMERIC,
    depth NUMERIC,
    description text COLLATE pg_catalog."default"
);

-- set up lake APA index table (stores processed GeoJSON with only APA value and location)

CREATE TABLE IF NOT EXISTS interface.lake_apa_index
(
    idx SERIAL PRIMARY KEY,
    lake_name text COLLATE pg_catalog."default" NOT NULL,
    geojson_data jsonb NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add capacitated AOI columns to existing area table (if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'interface' AND table_name = 'area' AND column_name = 'is_capacitated') THEN
        ALTER TABLE interface.area ADD COLUMN is_capacitated boolean DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'interface' AND table_name = 'area' AND column_name = 'lake_name') THEN
        ALTER TABLE interface.area ADD COLUMN lake_name text;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'interface' AND table_name = 'area' AND column_name = 'cluster_id') THEN
        ALTER TABLE interface.area ADD COLUMN cluster_id integer;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'interface' AND table_name = 'area' AND column_name = 'cluster_total_volume') THEN
        ALTER TABLE interface.area ADD COLUMN cluster_total_volume NUMERIC;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'interface' AND table_name = 'area' AND column_name = 'harvester_capacity') THEN
        ALTER TABLE interface.area ADD COLUMN harvester_capacity NUMERIC;
    END IF;
END $$;