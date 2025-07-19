CREATE TABLE IF NOT EXISTS transactions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  amount NUMERIC(10,2) NOT NULL,
  category TEXT,
  ts TIMESTAMP DEFAULT NOW()
);

INSERT INTO transactions (user_id, amount, category) VALUES
  (1, 25.50, 'groceries'),
  (1, 13.20, 'coffee'),
  (2, 199.99, 'electronics'),
  (3, 58.42, 'books'),
  (2, 12.00, 'coffee'),
  (4, 600.00, 'travel'),
  (3, 42.10, 'groceries');