CREATE DATABASE IF NOT EXISTS plant_care_db;
USE plant_care_db;

-- USERS -------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SUPPORT MESSAGES --------------------------------------
CREATE TABLE IF NOT EXISTS support_message (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DIAGNOSIS HISTORY -------------------------------------
CREATE TABLE IF NOT EXISTS diagnosis_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    disease_name VARCHAR(200) NOT NULL,
    cause TEXT,
    cure TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- PRODUCTS ----------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(500) DEFAULT '',
    stock INT DEFAULT 100
);

-- ORDERS ------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(200),
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- SEED PRODUCTS -----------------------------------------
INSERT INTO products (name, description, category, price, stock) VALUES
('Copper Oxychloride Fungicide', 'Broad-spectrum copper fungicide. Effective against bacterial spot, leaf spot and blights on tomato, pepper, citrus and more.', 'Fungicide', 349.00, 120),
('Neem Oil Concentrate', 'Cold-pressed organic neem oil for fungal diseases, mites, aphids and whiteflies. Safe for organic farming.', 'Organic', 279.00, 200),
('Mancozeb 75% WP', 'Protective contact fungicide for early blight, late blight, rust and leaf spots.', 'Fungicide', 299.00, 150),
('Streptocycline Bactericide', 'Antibiotic-based bactericide for bacterial spot, bacterial blight and canker.', 'Bactericide', 199.00, 80),
('Sulfur 80% WDG', 'Powdery mildew specialist. Also controls mites and scab.', 'Fungicide', 259.00, 100),
('Imidacloprid 17.8% SL', 'Systemic insecticide for whiteflies, aphids and thrips that spread viral diseases.', 'Pesticide', 389.00, 90),
('Trichoderma Viride Bio-fungicide', 'Bio-control agent that protects roots from soil-borne fungal pathogens.', 'Organic', 199.00, 150),
('NPK 19:19:19 Fertilizer', 'Water-soluble balanced fertilizer to boost plant immunity and recovery.', 'Fertilizer', 449.00, 180),
('Bypass Pruning Shears', 'Stainless steel bypass pruners for removing diseased branches. Clean cuts reduce reinfection.', 'Tool', 699.00, 60),
('Yellow Sticky Traps (Pack of 10)', 'Non-toxic sticky traps for monitoring and controlling whiteflies, aphids and fungus gnats.', 'Tool', 149.00, 200);