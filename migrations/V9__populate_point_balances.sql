-- Migration to populate point_balances table from existing points data
-- Run this once after creating the point_balances table

INSERT INTO point_balances (discord_id, current_balance, last_updated, last_transaction_id)
SELECT 
    p.discord_id,
    SUM(p.change_value) as current_balance,
    NOW() as last_updated,
    (SELECT MAX(p2.id) 
     FROM points p2 
     WHERE p2.discord_id = p.discord_id) as last_transaction_id
FROM points p
GROUP BY p.discord_id
ON CONFLICT (discord_id) DO NOTHING;

-- Verify the migration worked
SELECT 
    COUNT(*) as total_users_with_balances,
    SUM(current_balance) as total_points_in_system
FROM point_balances;