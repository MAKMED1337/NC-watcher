SELECT MAX(block_id) INTO @last_block FROM watcher_dev.ProcessedBlocks;
DELETE FROM watcher_dev.ProcessedBlocks WHERE processed = 1 AND block_id < @last_block;