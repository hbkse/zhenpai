-- Remove foreign key constraint on cs_match_id to allow bets before match is in cs2_matches table
ALTER TABLE cs2_match_bets DROP CONSTRAINT cs2_match_bets_cs_match_id_fkey;
