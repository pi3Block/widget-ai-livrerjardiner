-- Étape 1 : Supprimer toutes les tables existantes (avec CASCADE pour supprimer les dépendances)
DROP TABLE IF EXISTS stock_movements CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS pending_orders CASCADE;
DROP TABLE IF EXISTS stock CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- Étape 2 : Créer la table products (avec une colonne pour l'image)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(50) UNIQUE NOT NULL, -- Ex. : "ROS-001"
    name VARCHAR(100) NOT NULL,           -- Ex. : "Rosier Rouge"
    description TEXT,                     -- Description détaillée
    category VARCHAR(50),                 -- Ex. : "Rosiers", "Arbustes", "Fleurs"
    unit_price DECIMAL(10, 2) NOT NULL,   -- Prix unitaire (ex. : 5.00)
    image_url VARCHAR(255),               -- URL ou chemin de l'image (ex. : "https://example.com/images/rosier-rouge.jpg")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Étape 3 : Créer la table stock
CREATE TABLE stock (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 0,
    stock_alert_threshold INTEGER DEFAULT 10, -- Seuil pour les alertes de stock bas
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Étape 4 : Créer la table stock_movements (historique des mouvements de stock)
CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    quantity_change INTEGER NOT NULL, -- Positif pour une entrée, négatif pour une sortie
    reason VARCHAR(100),             -- Ex. : "Commande", "Réapprovisionnement"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Étape 5 : Créer la table orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    delivery_method VARCHAR(50) NOT NULL, -- Ex. : "livraison", "retrait"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Étape 6 : Créer la table pending_orders
CREATE TABLE pending_orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Étape 7 : Ajouter des index pour améliorer les performances
CREATE INDEX idx_products_reference ON products(reference);
CREATE INDEX idx_products_name ON products(LOWER(name));
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_stock_product_id ON stock(product_id);
CREATE INDEX idx_orders_product_id ON orders(product_id);
CREATE INDEX idx_pending_orders_product_id ON pending_orders(product_id);
CREATE INDEX idx_stock_movements_product_id ON stock_movements(product_id);