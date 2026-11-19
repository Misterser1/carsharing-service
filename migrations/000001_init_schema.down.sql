-- =============================================================================
-- 000001_init_schema (down): откат схемы.
-- Порядок обратный созданию: сначала таблицы, которые ссылаются на другие,
-- затем таблицы, на которые ссылаются; в конце ENUM-типы. Индексы удаляются вместе с таблицами.
-- ВНИМАНИЕ: откат удаляет все данные этих таблиц.
-- =============================================================================

DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS maintenance_records;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS deposit_holds;
DROP TABLE IF EXISTS vehicle_readings;
DROP TABLE IF EXISTS rentals;
DROP TABLE IF EXISTS tariffs;
DROP TABLE IF EXISTS vehicle_features;
DROP TABLE IF EXISTS features;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS vehicle_models;
DROP TABLE IF EXISTS vehicle_classes;
DROP TABLE IF EXISTS driver_profiles;
DROP TABLE IF EXISTS users;

DROP TYPE IF EXISTS incident_status;
DROP TYPE IF EXISTS maintenance_type;
DROP TYPE IF EXISTS payment_status;
DROP TYPE IF EXISTS payment_type;
DROP TYPE IF EXISTS deposit_status;
DROP TYPE IF EXISTS reading_source;
DROP TYPE IF EXISTS rental_status;
DROP TYPE IF EXISTS vehicle_status;
DROP TYPE IF EXISTS fuel_type;
DROP TYPE IF EXISTS transmission;
DROP TYPE IF EXISTS license_status;
DROP TYPE IF EXISTS user_status;
DROP TYPE IF EXISTS user_role;
