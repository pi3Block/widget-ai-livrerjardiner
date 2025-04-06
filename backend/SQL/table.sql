-- ======================================================
-- Schéma Base de Données V3 - LivrerJardiner.fr
-- ======================================================

-- Supprimer les anciennes tables (si elles existent) dans un ordre qui respecte les dépendances
-- Note: CASCADE supprime aussi les objets dépendants (contraintes, vues, etc.)
DROP TABLE IF EXISTS quote_items CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS stock_movements CASCADE;
DROP TABLE IF EXISTS stock CASCADE;
DROP TABLE IF EXISTS product_variant_tags CASCADE;
DROP TABLE IF EXISTS product_variants CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS quotes CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS pending_orders CASCADE; -- Assurer la suppression de l'ancienne table

-- ------------------------------------------------------
-- Table: users
-- ------------------------------------------------------
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Stocker un hash sécurisé
    name VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: addresses
-- ------------------------------------------------------
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: categories
-- ------------------------------------------------------
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL, -- Pour la hiérarchie
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: products
-- (Informations générales sur le produit)
-- ------------------------------------------------------
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    base_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: product_variants
-- (Variations spécifiques d'un produit : taille, couleur, SKU, prix)
-- ------------------------------------------------------
CREATE TABLE product_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(100) UNIQUE NOT NULL, -- Stock Keeping Unit (Référence unique pour cette variation)
    attributes JSONB,                  -- Ex: {'size': 'M', 'color': 'Red'}
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    image_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: tags
-- ------------------------------------------------------
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- ------------------------------------------------------
-- Table: product_variant_tags (Many-to-Many)
-- ------------------------------------------------------
CREATE TABLE product_variant_tags (
    product_variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (product_variant_id, tag_id)
);

-- ------------------------------------------------------
-- Table: stock
-- (Stock par variation de produit)
-- ------------------------------------------------------
CREATE TABLE stock (
    product_variant_id INTEGER PRIMARY KEY REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    stock_alert_threshold INTEGER DEFAULT 10,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: orders
-- (En-tête de commande)
-- ------------------------------------------------------
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT, -- Ne pas supprimer un user qui a des commandes
    order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- Ex: pending, processing, shipped, delivered, cancelled
    total_amount DECIMAL(12, 2) NOT NULL CHECK (total_amount >= 0),
    delivery_address_id INTEGER NOT NULL REFERENCES addresses(id) ON DELETE RESTRICT,
    billing_address_id INTEGER NOT NULL REFERENCES addresses(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: order_items
-- (Lignes d'une commande)
-- ------------------------------------------------------
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT, -- Garder trace même si variation supprimée ? Ou SET NULL ? RESTRICT est plus sûr pour commencer.
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_at_order DECIMAL(10, 2) NOT NULL CHECK (price_at_order >= 0), -- Prix au moment de la commande
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: stock_movements
-- (Historique des mouvements de stock par variation)
-- ------------------------------------------------------
CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    product_variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity_change INTEGER NOT NULL, -- Négatif pour sortie, Positif pour entrée
    movement_type VARCHAR(50) NOT NULL, -- Ex: 'order_fulfillment', 'restock', 'inventory_adjustment', 'return'
    order_item_id INTEGER REFERENCES order_items(id) ON DELETE SET NULL, -- Lien optionnel vers la ligne de commande concernée
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: quotes
-- (En-tête de devis)
-- ------------------------------------------------------
CREATE TABLE quotes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quote_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- Ex: pending, accepted, rejected, expired
    expires_at TIMESTAMP WITH TIME ZONE,         -- Date d'expiration optionnelle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------
-- Table: quote_items
-- (Lignes d'un devis)
-- ------------------------------------------------------
CREATE TABLE quote_items (
    id SERIAL PRIMARY KEY,
    quote_id INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    product_variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE, -- Si la variation est suppr, le devis n'est plus valide
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_at_quote DECIMAL(10, 2) NOT NULL CHECK (price_at_quote >= 0), -- Prix au moment du devis
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ======================================================
-- INDEX
-- ======================================================

-- users
CREATE INDEX idx_users_email ON users(email);

-- addresses
CREATE INDEX idx_addresses_user_id ON addresses(user_id);

-- categories
CREATE INDEX idx_categories_name ON categories(name);
CREATE INDEX idx_categories_parent_id ON categories(parent_category_id);

-- products
CREATE INDEX idx_products_name ON products(LOWER(name));
CREATE INDEX idx_products_category_id ON products(category_id);

-- product_variants
CREATE INDEX idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX idx_product_variants_sku ON product_variants(sku);
-- Index GIN pour recherches dans JSONB (si PostgreSQL >= 9.4)
CREATE INDEX idx_product_variants_attributes ON product_variants USING GIN (attributes);

-- product_variant_tags
CREATE INDEX idx_product_variant_tags_tag_id ON product_variant_tags(tag_id);
-- L'index sur (product_variant_id, tag_id) est créé par la PK

-- tags
CREATE INDEX idx_tags_name ON tags(name);

-- stock
-- L'index sur product_variant_id est créé par la PK

-- orders
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_order_date ON orders(order_date);

-- order_items
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_variant_id ON order_items(product_variant_id);

-- stock_movements
CREATE INDEX idx_stock_movements_product_variant_id ON stock_movements(product_variant_id);
CREATE INDEX idx_stock_movements_movement_type ON stock_movements(movement_type);
CREATE INDEX idx_stock_movements_created_at ON stock_movements(created_at);

-- quotes
CREATE INDEX idx_quotes_user_id ON quotes(user_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_expires_at ON quotes(expires_at);

-- quote_items
CREATE INDEX idx_quote_items_quote_id ON quote_items(quote_id);
CREATE INDEX idx_quote_items_product_variant_id ON quote_items(product_variant_id);


-- ======================================================
-- FONCTIONS TRIGGER (Optionnel, pour updated_at)
-- ======================================================

-- Fonction pour mettre à jour automatiquement le champ updated_at
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Appliquer le trigger aux tables concernées
CREATE TRIGGER set_timestamp_users BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_addresses BEFORE UPDATE ON addresses FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_categories BEFORE UPDATE ON categories FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_products BEFORE UPDATE ON products FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_product_variants BEFORE UPDATE ON product_variants FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
-- stock n'a pas updated_at, mais last_updated géré par CRUD
CREATE TRIGGER set_timestamp_orders BEFORE UPDATE ON orders FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_order_items BEFORE UPDATE ON order_items FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_quotes BEFORE UPDATE ON quotes FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();
CREATE TRIGGER set_timestamp_quote_items BEFORE UPDATE ON quote_items FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();

-- FIN DU SCRIPT