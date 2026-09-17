-- =============================================================================
-- Сервис аренды автомобилей (Carsharing / Rental API) — схема БД, PostgreSQL 16
-- Лабораторная работа №1, вариант 5. Схема в 3-й нормальной форме (3NF).
--
-- Запуск: psql -U postgres -d carsharing -f db/schema.sql
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

-- -----------------------------------------------------------------------------
-- Перечисления (ENUM)
-- -----------------------------------------------------------------------------
CREATE TYPE user_role        AS ENUM ('DRIVER', 'OPERATOR', 'ADMIN');
CREATE TYPE user_status      AS ENUM ('ACTIVE', 'BLOCKED');
CREATE TYPE license_status   AS ENUM ('PENDING', 'VERIFIED', 'REJECTED');
CREATE TYPE transmission     AS ENUM ('MANUAL', 'AUTOMATIC');
CREATE TYPE fuel_type        AS ENUM ('PETROL', 'DIESEL', 'ELECTRIC', 'HYBRID');
CREATE TYPE vehicle_status   AS ENUM ('AVAILABLE', 'RESERVED', 'RENTED', 'MAINTENANCE', 'DECOMMISSIONED');
CREATE TYPE rental_status    AS ENUM ('RESERVED', 'ACTIVE', 'COMPLETED', 'CANCELLED', 'EXPIRED');
CREATE TYPE reading_source   AS ENUM ('TELEMATICS', 'RENTAL_START', 'RENTAL_END', 'MANUAL');
CREATE TYPE deposit_status   AS ENUM ('HELD', 'RELEASED', 'CAPTURED', 'PARTIALLY_CAPTURED', 'FAILED');
CREATE TYPE payment_type     AS ENUM ('RENTAL_CHARGE', 'FINE', 'DEPOSIT_CAPTURE', 'REFUND');
CREATE TYPE payment_status   AS ENUM ('PENDING', 'SUCCEEDED', 'FAILED', 'REFUNDED');
CREATE TYPE maintenance_type AS ENUM ('SERVICE', 'REPAIR', 'REFUEL', 'CLEANING', 'INSPECTION');
CREATE TYPE incident_status  AS ENUM ('OPEN', 'UNDER_REVIEW', 'RESOLVED', 'REJECTED');

-- -----------------------------------------------------------------------------
-- Пользователи
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id            UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255)  NOT NULL,
    phone         VARCHAR(20)   NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    full_name     VARCHAR(150)  NOT NULL,
    role          user_role     NOT NULL DEFAULT 'DRIVER',
    status        user_status   NOT NULL DEFAULT 'ACTIVE',
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),

    CONSTRAINT ck_users_email_lower CHECK (email = lower(email)),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_phone UNIQUE (phone)
);
CREATE INDEX ix_users_role ON users (role);

COMMENT ON TABLE users IS 'Учётные записи: водители, операторы автопарка, администраторы';

CREATE TABLE driver_profiles (
    user_id            UUID           PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    birth_date         DATE           NOT NULL,
    license_number     VARCHAR(20)    NOT NULL,
    license_issued_at  DATE           NOT NULL,
    license_expires_at DATE           NOT NULL,
    license_status     license_status NOT NULL DEFAULT 'PENDING',
    license_scan_key   VARCHAR(255),                                  -- ключ файла в S3
    verified_by        UUID           REFERENCES users (id) ON DELETE SET NULL,
    verified_at        TIMESTAMPTZ,

    CONSTRAINT uq_driver_profiles_license UNIQUE (license_number),
    CONSTRAINT ck_driver_profiles_license_dates CHECK (license_expires_at > license_issued_at),
    CONSTRAINT ck_driver_profiles_age CHECK (birth_date <= CURRENT_DATE - INTERVAL '18 years'),
    CONSTRAINT ck_driver_profiles_verified CHECK (
        (license_status = 'VERIFIED' AND verified_by IS NOT NULL AND verified_at IS NOT NULL)
        OR license_status <> 'VERIFIED'
    )
);
CREATE INDEX ix_driver_profiles_status ON driver_profiles (license_status);
CREATE INDEX ix_driver_profiles_verified_by ON driver_profiles (verified_by);

COMMENT ON TABLE driver_profiles IS 'Профиль водителя (1:1 к users): данные водительского удостоверения';

-- -----------------------------------------------------------------------------
-- Автопарк
-- -----------------------------------------------------------------------------
CREATE TABLE vehicle_classes (
    id   SMALLSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(50) NOT NULL,

    CONSTRAINT uq_vehicle_classes_code UNIQUE (code)
);
COMMENT ON TABLE vehicle_classes IS 'Классы автомобилей (ECONOMY, COMFORT, BUSINESS, SUV) — основа тарификации';

CREATE TABLE vehicle_models (
    id              SERIAL        PRIMARY KEY,
    class_id        SMALLINT      NOT NULL REFERENCES vehicle_classes (id),
    brand           VARCHAR(50)   NOT NULL,
    model           VARCHAR(50)   NOT NULL,
    seats           SMALLINT      NOT NULL,
    transmission    transmission  NOT NULL,
    fuel_type       fuel_type     NOT NULL,
    tank_capacity_l NUMERIC(5,1),

    CONSTRAINT uq_vehicle_models_brand_model UNIQUE (brand, model),
    CONSTRAINT ck_vehicle_models_seats CHECK (seats BETWEEN 1 AND 9),
    CONSTRAINT ck_vehicle_models_tank CHECK (tank_capacity_l IS NULL OR tank_capacity_l > 0)
);
CREATE INDEX ix_vehicle_models_class ON vehicle_models (class_id);

COMMENT ON TABLE vehicle_models IS 'Справочник марок / моделей автомобилей';

CREATE TABLE locations (
    id        SERIAL        PRIMARY KEY,
    name      VARCHAR(100)  NOT NULL,
    address   VARCHAR(255)  NOT NULL,
    latitude  NUMERIC(9,6)  NOT NULL,
    longitude NUMERIC(9,6)  NOT NULL,
    capacity  SMALLINT      NOT NULL,
    is_active BOOLEAN       NOT NULL DEFAULT TRUE,

    CONSTRAINT ck_locations_lat CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_locations_lng CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT ck_locations_capacity CHECK (capacity > 0)
);
COMMENT ON TABLE locations IS 'Парковки / зоны выдачи и возврата автомобилей';

CREATE TABLE vehicles (
    id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id       INTEGER        NOT NULL REFERENCES vehicle_models (id),
    location_id    INTEGER        REFERENCES locations (id) ON DELETE SET NULL,   -- NULL, пока авто в поездке
    plate_number   VARCHAR(12)    NOT NULL,
    vin            CHAR(17)       NOT NULL,
    year           SMALLINT       NOT NULL,
    color          VARCHAR(30)    NOT NULL,
    status         vehicle_status NOT NULL DEFAULT 'AVAILABLE',
    odometer_km    INTEGER        NOT NULL DEFAULT 0,      -- текущий пробег
    fuel_level_pct SMALLINT       NOT NULL DEFAULT 100,    -- текущий уровень топлива / заряда, %
    latitude       NUMERIC(9,6),
    longitude      NUMERIC(9,6),
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT ck_vehicles_plate_upper CHECK (plate_number = upper(plate_number)),
    CONSTRAINT uq_vehicles_plate_number UNIQUE (plate_number),
    CONSTRAINT uq_vehicles_vin UNIQUE (vin),
    CONSTRAINT ck_vehicles_year CHECK (year BETWEEN 2000 AND 2100),
    CONSTRAINT ck_vehicles_odometer CHECK (odometer_km >= 0),
    CONSTRAINT ck_vehicles_fuel CHECK (fuel_level_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_vehicles_lat CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_vehicles_lng CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);
CREATE INDEX ix_vehicles_status          ON vehicles (status);
CREATE INDEX ix_vehicles_model           ON vehicles (model_id);
CREATE INDEX ix_vehicles_location        ON vehicles (location_id);
CREATE INDEX ix_vehicles_status_location ON vehicles (status, location_id);   -- поиск свободных авто на парковке

COMMENT ON TABLE vehicles IS 'Автомобили автопарка: статус доступности, текущие пробег и уровень топлива';

CREATE TABLE features (
    id   SMALLSERIAL  PRIMARY KEY,
    code VARCHAR(30)  NOT NULL,
    name VARCHAR(100) NOT NULL,

    CONSTRAINT uq_features_code UNIQUE (code)
);
COMMENT ON TABLE features IS 'Справочник опций оснащения (CHILD_SEAT, GPS, WINTER_TIRES, ...)';

-- Связь N:M автомобиль <-> опция
CREATE TABLE vehicle_features (
    vehicle_id UUID     NOT NULL REFERENCES vehicles (id) ON DELETE CASCADE,
    feature_id SMALLINT NOT NULL REFERENCES features (id) ON DELETE CASCADE,

    CONSTRAINT pk_vehicle_features PRIMARY KEY (vehicle_id, feature_id)
);
CREATE INDEX ix_vehicle_features_feature ON vehicle_features (feature_id);

-- -----------------------------------------------------------------------------
-- Тарифы
-- -----------------------------------------------------------------------------
CREATE TABLE tariffs (
    id               SERIAL         PRIMARY KEY,
    class_id         SMALLINT       NOT NULL REFERENCES vehicle_classes (id),
    name             VARCHAR(100)   NOT NULL,
    price_per_minute NUMERIC(10,2)  NOT NULL,
    price_per_km     NUMERIC(10,2)  NOT NULL,
    price_per_day    NUMERIC(10,2)  NOT NULL,
    deposit_amount   NUMERIC(10,2)  NOT NULL,     -- сумма блокировки депозита
    currency         CHAR(3)        NOT NULL DEFAULT 'RUB',
    valid_from       TIMESTAMPTZ    NOT NULL DEFAULT now(),
    valid_to         TIMESTAMPTZ,                 -- NULL = бессрочно
    is_active        BOOLEAN        NOT NULL DEFAULT TRUE,

    CONSTRAINT ck_tariffs_prices CHECK (
        price_per_minute >= 0 AND price_per_km >= 0 AND price_per_day >= 0 AND deposit_amount >= 0
    ),
    CONSTRAINT ck_tariffs_period CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX ix_tariffs_class_active ON tariffs (class_id, is_active);

COMMENT ON TABLE tariffs IS 'Тарифы по классу авто; история изменений хранится через valid_from / valid_to';

-- -----------------------------------------------------------------------------
-- Аренды
-- -----------------------------------------------------------------------------
CREATE TABLE rentals (
    id                     UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id              UUID          NOT NULL REFERENCES users (id),
    vehicle_id             UUID          NOT NULL REFERENCES vehicles (id),
    tariff_id              INTEGER       NOT NULL REFERENCES tariffs (id),   -- тариф на момент брони
    start_location_id      INTEGER       REFERENCES locations (id),
    end_location_id        INTEGER       REFERENCES locations (id),
    status                 rental_status NOT NULL DEFAULT 'RESERVED',
    reserved_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    reservation_expires_at TIMESTAMPTZ   NOT NULL,
    started_at             TIMESTAMPTZ,
    ended_at               TIMESTAMPTZ,
    start_odometer_km      INTEGER,
    end_odometer_km        INTEGER,
    start_fuel_pct         SMALLINT,
    end_fuel_pct           SMALLINT,
    total_amount           NUMERIC(10,2),   -- итоговая сумма, фиксируется при завершении

    CONSTRAINT ck_rentals_reservation CHECK (reservation_expires_at > reserved_at),
    CONSTRAINT ck_rentals_times CHECK (
        (started_at IS NULL OR started_at >= reserved_at)
        AND (ended_at IS NULL OR (started_at IS NOT NULL AND ended_at >= started_at))
    ),
    CONSTRAINT ck_rentals_odometer CHECK (
        (start_odometer_km IS NULL OR start_odometer_km >= 0)
        AND (end_odometer_km IS NULL OR end_odometer_km >= start_odometer_km)
    ),
    CONSTRAINT ck_rentals_fuel CHECK (
        (start_fuel_pct IS NULL OR start_fuel_pct BETWEEN 0 AND 100)
        AND (end_fuel_pct IS NULL OR end_fuel_pct BETWEEN 0 AND 100)
    ),
    CONSTRAINT ck_rentals_total CHECK (total_amount IS NULL OR total_amount >= 0),
    -- завершённая аренда обязана иметь показания старта и финиша
    CONSTRAINT ck_rentals_completed CHECK (
        status <> 'COMPLETED'
        OR (started_at IS NOT NULL AND ended_at IS NOT NULL
            AND start_odometer_km IS NOT NULL AND end_odometer_km IS NOT NULL
            AND start_fuel_pct IS NOT NULL AND end_fuel_pct IS NOT NULL
            AND total_amount IS NOT NULL)
    )
);
CREATE INDEX ix_rentals_driver          ON rentals (driver_id);
CREATE INDEX ix_rentals_vehicle         ON rentals (vehicle_id);
CREATE INDEX ix_rentals_tariff          ON rentals (tariff_id);
CREATE INDEX ix_rentals_start_location  ON rentals (start_location_id);
CREATE INDEX ix_rentals_end_location    ON rentals (end_location_id);
CREATE INDEX ix_rentals_status_expires  ON rentals (status, reservation_expires_at);   -- worker: истёкшие резервы
CREATE INDEX ix_rentals_driver_reserved ON rentals (driver_id, reserved_at DESC);      -- история поездок

-- Не более одной незавершённой аренды на автомобиль и на водителя (частичные уникальные индексы)
CREATE UNIQUE INDEX ux_rentals_vehicle_open ON rentals (vehicle_id) WHERE status IN ('RESERVED', 'ACTIVE');
CREATE UNIQUE INDEX ux_rentals_driver_open  ON rentals (driver_id)  WHERE status IN ('RESERVED', 'ACTIVE');

COMMENT ON TABLE rentals IS 'Аренда: RESERVED -> ACTIVE -> COMPLETED | CANCELLED | EXPIRED';

CREATE TABLE vehicle_readings (
    id             BIGSERIAL      PRIMARY KEY,
    vehicle_id     UUID           NOT NULL REFERENCES vehicles (id) ON DELETE CASCADE,
    rental_id      UUID           REFERENCES rentals (id) ON DELETE SET NULL,   -- NULL вне аренды
    source         reading_source NOT NULL,
    odometer_km    INTEGER        NOT NULL,
    fuel_level_pct SMALLINT       NOT NULL,
    latitude       NUMERIC(9,6),
    longitude      NUMERIC(9,6),
    recorded_at    TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT ck_vehicle_readings_odometer CHECK (odometer_km >= 0),
    CONSTRAINT ck_vehicle_readings_fuel CHECK (fuel_level_pct BETWEEN 0 AND 100)
);
CREATE INDEX ix_vehicle_readings_vehicle_time ON vehicle_readings (vehicle_id, recorded_at DESC);
CREATE INDEX ix_vehicle_readings_rental       ON vehicle_readings (rental_id);

COMMENT ON TABLE vehicle_readings IS 'Журнал показаний одометра, уровня топлива и GPS';

-- -----------------------------------------------------------------------------
-- Деньги
-- -----------------------------------------------------------------------------
CREATE TABLE deposit_holds (
    id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    rental_id        UUID           NOT NULL REFERENCES rentals (id),
    amount           NUMERIC(10,2)  NOT NULL,
    currency         CHAR(3)        NOT NULL,
    status           deposit_status NOT NULL DEFAULT 'HELD',
    captured_amount  NUMERIC(10,2)  NOT NULL DEFAULT 0,
    provider_hold_id VARCHAR(100)   NOT NULL,   -- id операции hold в платёжном шлюзе
    held_at          TIMESTAMPTZ    NOT NULL DEFAULT now(),
    released_at      TIMESTAMPTZ,

    CONSTRAINT uq_deposit_holds_rental UNIQUE (rental_id),          -- 1:1 с арендой
    CONSTRAINT uq_deposit_holds_provider UNIQUE (provider_hold_id),
    CONSTRAINT ck_deposit_holds_amount CHECK (amount > 0),
    CONSTRAINT ck_deposit_holds_captured CHECK (captured_amount >= 0 AND captured_amount <= amount),
    CONSTRAINT ck_deposit_holds_released CHECK (released_at IS NULL OR released_at >= held_at)
);
CREATE INDEX ix_deposit_holds_status ON deposit_holds (status);

COMMENT ON TABLE deposit_holds IS 'Блокировка депозита по аренде: HELD -> RELEASED | CAPTURED | PARTIALLY_CAPTURED';

CREATE TABLE payments (
    id                      UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    rental_id               UUID           NOT NULL REFERENCES rentals (id),
    type                    payment_type   NOT NULL,
    status                  payment_status NOT NULL DEFAULT 'PENDING',
    amount                  NUMERIC(10,2)  NOT NULL,
    currency                CHAR(3)        NOT NULL,
    provider_transaction_id VARCHAR(100),
    created_at              TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT uq_payments_provider_tx UNIQUE (provider_transaction_id),
    CONSTRAINT ck_payments_amount CHECK (amount > 0)
);
CREATE INDEX ix_payments_rental         ON payments (rental_id);
CREATE INDEX ix_payments_status_created ON payments (status, created_at);

COMMENT ON TABLE payments IS 'Платежи по аренде: оплата поездки, штраф, удержание депозита, возврат';

-- -----------------------------------------------------------------------------
-- Эксплуатация
-- -----------------------------------------------------------------------------
CREATE TABLE maintenance_records (
    id          BIGSERIAL        PRIMARY KEY,
    vehicle_id  UUID             NOT NULL REFERENCES vehicles (id) ON DELETE CASCADE,
    operator_id UUID             NOT NULL REFERENCES users (id),
    type        maintenance_type NOT NULL,
    description TEXT,
    cost        NUMERIC(10,2),
    odometer_km INTEGER          NOT NULL,   -- пробег на момент работ
    started_at  TIMESTAMPTZ      NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,

    CONSTRAINT ck_maintenance_cost CHECK (cost IS NULL OR cost >= 0),
    CONSTRAINT ck_maintenance_odometer CHECK (odometer_km >= 0),
    CONSTRAINT ck_maintenance_times CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX ix_maintenance_vehicle_time ON maintenance_records (vehicle_id, started_at DESC);
CREATE INDEX ix_maintenance_operator     ON maintenance_records (operator_id);

COMMENT ON TABLE maintenance_records IS 'ТО, ремонт, заправка, мойка — переводят авто в статус MAINTENANCE';

CREATE TABLE incidents (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    rental_id   UUID            NOT NULL REFERENCES rentals (id),
    reported_by UUID            NOT NULL REFERENCES users (id),
    resolved_by UUID            REFERENCES users (id),
    status      incident_status NOT NULL DEFAULT 'OPEN',
    description TEXT            NOT NULL,
    fine_amount NUMERIC(10,2),   -- сумма к удержанию из депозита
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,

    CONSTRAINT ck_incidents_fine CHECK (fine_amount IS NULL OR fine_amount >= 0),
    CONSTRAINT ck_incidents_resolved CHECK (
        (status IN ('RESOLVED', 'REJECTED') AND resolved_by IS NOT NULL AND resolved_at IS NOT NULL)
        OR status IN ('OPEN', 'UNDER_REVIEW')
    )
);
CREATE INDEX ix_incidents_rental         ON incidents (rental_id);
CREATE INDEX ix_incidents_reported_by    ON incidents (reported_by);
CREATE INDEX ix_incidents_status_created ON incidents (status, created_at);

COMMENT ON TABLE incidents IS 'Повреждения, штрафы, спорные ситуации по аренде';

-- -----------------------------------------------------------------------------
-- Справочные данные
-- -----------------------------------------------------------------------------
INSERT INTO vehicle_classes (code, name) VALUES
    ('ECONOMY',  'Эконом'),
    ('COMFORT',  'Комфорт'),
    ('BUSINESS', 'Бизнес'),
    ('SUV',      'Кроссовер / внедорожник');

INSERT INTO features (code, name) VALUES
    ('CHILD_SEAT',   'Детское кресло'),
    ('GPS',          'Навигатор'),
    ('WINTER_TIRES', 'Зимняя резина'),
    ('ROOF_RACK',    'Багажник на крыше'),
    ('PET_FRIENDLY', 'Разрешена перевозка животных');

COMMIT;
