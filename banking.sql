-- ═══════════════════════════════════════════
-- TABLE CREATION (schema.sql)
-- ═══════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS banking_db;
USE banking_db;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL CHECK (username REGEXP '^[A-Za-z_]+$'),
    password VARCHAR(255) NOT NULL,
    role TEXT NOT NULL
);


CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE,
    full_name VARCHAR(100) NOT NULL CHECK (full_name REGEXP '^[A-Za-z ]+$'),
    email VARCHAR(100),
    phone VARCHAR(15) CHECK (phone IS NULL OR phone = '' OR phone REGEXP '^[0-9]{7,15}$'),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    balance DECIMAL(10,2) DEFAULT 0.00 CHECK (balance >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT,
    type ENUM('deposit', 'withdraw', 'transfer') NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    related_account_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- ═══════════════════════════════════════════
-- INSERT
-- ═══════════════════════════════════════════

-- Create new user login (when admin adds customer)
INSERT INTO users (username, password, role)
VALUES (%s, %s, 'customer');

-- Create customer profile
INSERT INTO customers (user_id, full_name, email, phone)
VALUES (%s, %s, %s, %s);

-- Open bank account for customer
INSERT INTO accounts (customer_id, account_number, balance)
VALUES (%s, %s, 0.00);

-- Log a deposit
INSERT INTO transactions (account_id, type, amount)
VALUES (%s, 'deposit', %s);

-- Log a withdrawal
INSERT INTO transactions (account_id, type, amount)
VALUES (%s, 'withdraw', %s);

-- Log a transfer (stores both from and to account)
INSERT INTO transactions (account_id, type, amount, related_account_id)
VALUES (%s, 'transfer', %s, %s);

-- ═══════════════════════════════════════════
-- SELECT
-- ═══════════════════════════════════════════

-- Login check
SELECT * FROM users WHERE username = %s;

-- Check if username already exists (before creating)
SELECT id FROM users WHERE username = %s;

-- Admin dashboard: get all customers with their account info
SELECT c.id, c.full_name, c.email, c.phone,
       a.account_number, a.balance, a.id as account_id
FROM customers c
LEFT JOIN accounts a ON c.id = a.customer_id;

-- Admin: get all transactions with customer and account info
SELECT t.id, t.type, t.amount, t.created_at,
       a.account_number, c.full_name
FROM transactions t
JOIN accounts a ON t.account_id = a.id
JOIN customers c ON a.customer_id = c.id
ORDER BY t.created_at DESC;

-- Customer dashboard: get own account info
SELECT c.full_name, c.email, c.phone,
       a.account_number, a.balance, a.id as account_id
FROM customers c
JOIN accounts a ON c.id = a.customer_id
WHERE c.user_id = %s;

-- Customer: get own transaction history (last 10)
SELECT type, amount, created_at, related_account_id
FROM transactions
WHERE account_id = %s
ORDER BY created_at DESC
LIMIT 10;

-- Get sender account for deposit/withdraw/transfer
SELECT a.id, a.balance, a.account_number
FROM accounts a
JOIN customers c ON a.customer_id = c.id
WHERE c.user_id = %s;

-- Find receiver account by account number (for transfer)
SELECT id FROM accounts WHERE account_number = %s;

-- ═══════════════════════════════════════════
-- UPDATE
-- ═══════════════════════════════════════════

-- Deposit: add money to account
UPDATE accounts SET balance = balance + %s WHERE id = %s;

-- Withdraw: deduct money from account
UPDATE accounts SET balance = balance - %s WHERE id = %s;

-- Transfer: deduct from sender
UPDATE accounts SET balance = balance - %s WHERE id = %s;

-- Transfer: add to receiver
UPDATE accounts SET balance = balance + %s WHERE id = %s;

-- ═══════════════════════════════════════════
-- DELETE
-- ═══════════════════════════════════════════

-- Delete all transactions of an account (before deleting customer)
DELETE FROM transactions WHERE account_id = %s;

-- Delete customer's accounts
DELETE FROM accounts WHERE customer_id = %s;

-- Delete customer profile
DELETE FROM customers WHERE id = %s;

-- Delete user login
DELETE FROM users WHERE id = %s;