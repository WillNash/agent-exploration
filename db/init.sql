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

CREATE TABLE developer_tokens (
    id          SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    name        TEXT NOT NULL,
    jti         TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX idx_dev_tokens_customer ON developer_tokens(customer_id);
CREATE INDEX idx_dev_tokens_jti      ON developer_tokens(jti);

-- Seed products
INSERT INTO products (name, description, price, category, stock_qty) VALUES
    ('Tomato Seeds (Heirloom)',    'Heritage beefsteak variety, excellent flavour. Sow indoors Feb–Apr; plant out after last frost.',                                           3.50,  'seeds',       200),
    ('Courgette Seeds',            'Fast-growing summer squash, prolific cropper. Sow indoors Apr–May; plant out Jun.',                                                          2.80,  'seeds',       150),
    ('Sunflower Seeds (Giant)',    'Grows to 3m, attracts pollinators. Sow direct Apr–May after last frost.',                                                                    2.20,  'seeds',       300),
    ('Basil Seeds',                'Sweet Genovese basil, ideal for containers. Sow indoors Mar–May; needs warmth, not frost-hardy.',                                            1.90,  'seeds',       250),
    ('Cucumber Seeds',             'Reliable outdoor ridge cucumber, prolific cropper. Sow indoors Mar–Apr; plant out after last frost.',                                        3.20,  'seeds',        80),
    ('Sweet Pepper Seeds',         'Mixed sweet peppers; needs a long warm season. Sow indoors Feb–Mar in warmth; transplant out Jun.',                                          3.50,  'seeds',        60),
    ('Pumpkin Seeds (Crown Prince)','Award-winning blue-grey pumpkin with superb flavour. Sow indoors Apr–May; plant out Jun; harvest Sep–Oct.',                                3.80,  'seeds',        50),
    ('Broad Bean Seeds (Aquadulce)','Classic overwintering variety, very frost-hardy. Sow direct Oct–Nov; harvest May–Jun. Best autumn-sown seed in the range.',                2.80,  'seeds',       120),
    ('Winter Spinach Seeds',       'Hardy perpetual spinach for autumn sowing. Sow Aug–Oct; crops through winter and into spring. Frost-tolerant.',                             2.20,  'seeds',       200),
    ('Kale Seeds (Dwarf Green Curled)','Extremely frost-hardy brassica. Sow Jul–Aug for autumn harvest or Sep–Oct for spring. Flavour improves after frost.',                   2.40,  'seeds',       150),
    ('Spring Onion Seeds (White Lisbon)','Winter-hardy salad onion. Sow Aug–Sep for an early spring harvest. Tolerates hard frosts.',                                           1.80,  'seeds',       300),
    ('Pak Choi Seeds',             'Fast-growing Asian green. Sow late summer (Aug–Sep) or under cover in autumn; bolts in heat.',                                              2.60,  'seeds',       175),
    ('Corn Salad Seeds (Mâche)',   'Extremely cold-hardy salad leaf. Sow Sep–Oct; harvests through winter even in hard frosts. Very easy to grow.',                             1.70,  'seeds',       400),
    ('Winter Lettuce Seeds (Arctic King)','Butterhead variety bred for cold tolerance. Sow Sep–Oct under cover or cold frame; harvest mid-winter.',                             2.30,  'seeds',       250),
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
