SELECT MAX(block_id) INTO @last_block FROM ProcessedBlocks;
DELETE FROM ProcessedBlocks WHERE processed = 1 AND block_id < @last_block;