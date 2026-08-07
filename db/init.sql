CREATE TABLE customers (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    price       NUMERIC(10, 2) NOT NULL,
    category    TEXT,
    stock_qty   INT NOT NULL DEFAULT 0
);

CREATE TABLE customer_purchases (
    id           SERIAL PRIMARY KEY,
    customer_id  INT NOT NULL REFERENCES customers(id),
    product_id   INT NOT NULL REFERENCES products(id),
    quantity     INT NOT NULL DEFAULT 1,
    purchased_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_purchases_customer ON customer_purchases(customer_id);

-- Seed products
INSERT INTO products (name, description, price, category, stock_qty) VALUES
    ('Tomato Seeds (Heirloom)',    'Heritage beefsteak variety, excellent flavour',       3.50,  'seeds',       200),
    ('Courgette Seeds',            'Fast-growing summer squash, prolific cropper',         2.80,  'seeds',       150),
    ('Sunflower Seeds (Giant)',    'Grows to 3m, attract pollinators',                    2.20,  'seeds',       300),
    ('Basil Seeds',                'Sweet Genovese basil, ideal for containers',           1.90,  'seeds',       250),
    ('Garden Fork',                'Stainless steel, ergonomic ash handle',               34.99, 'tools',        40),
    ('Hand Trowel',                'Solid forged trowel with depth markings',             14.50, 'tools',        80),
    ('Watering Can (9L)',          'Galvanised steel with detachable rose head',          22.00, 'tools',        35),
    ('Pruning Shears',             'Bypass action, rust-resistant blades',               18.75, 'tools',        60),
    ('Terracotta Pot (20cm)',      'Classic frost-proof terracotta, drainage hole',        6.00, 'pots',        120),
    ('Hanging Basket (35cm)',      'Coco-lined with pre-attached chains',                  8.50, 'pots',         90),
    ('Window Box (60cm)',          'Self-watering plastic window box, dark green',        12.00, 'pots',         75),
    ('Slow-Release Fertiliser',   'Balanced NPK granules, feeds for 6 months',           11.99, 'fertilisers',  50),
    ('Liquid Tomato Feed (1L)',    'High-potash weekly feed for fruiting plants',          7.50, 'fertilisers',  65),
    ('Seaweed Extract (500ml)',    'Natural growth stimulant and soil conditioner',        9.25, 'fertilisers',  45),
    ('Peat-Free Compost (40L)',    'RHS-approved multi-purpose peat-free compost',        8.99, 'compost',       80);

-- Seed customers
INSERT INTO customers (name, email) VALUES
    ('Alice Green', 'alice@example.com'),
    ('Bob Trowel',  'bob@example.com');
