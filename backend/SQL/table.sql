-- Table pour les devis
CREATE TABLE quotes (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(100),
    item VARCHAR(50),
    quantity INT,
    unit_price DECIMAL(10, 2),
    total_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pdf_path VARCHAR(255)  -- Chemin vers le PDF du devis
);

-- Table pour les commandes en attente (si pas en stock)
CREATE TABLE pending_orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(100),
    item VARCHAR(50),
    quantity INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour les commandes confirmées
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(100),
    item VARCHAR(50),
    quantity INT,
    delivery_method VARCHAR(20),  -- "livraison" ou "retrait"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);