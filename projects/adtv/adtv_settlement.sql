CREATE OR REPLACE FUNCTION process_daily_settlement(target_date DATE)
RETURNS VOID AS $$
DECLARE
    total_rev DECIMAL(18,4);
    user_pool DECIMAL(18,4);
    platform_share DECIMAL(18,4);
    total_cu DECIMAL(18,6);
    cu_rate DECIMAL(18,8);
BEGIN

    -- 1. Total Verified Revenue
    SELECT COALESCE(SUM(cpv),0)
    INTO total_rev
    FROM revenue_events
    WHERE verified = TRUE
    AND DATE(created_at) = target_date;

    platform_share := total_rev * 0.45;
    user_pool := total_rev * 0.55;

    -- 2. Total CU Issued
    SELECT COALESCE(SUM(cu_amount),0)
    INTO total_cu
    FROM cu_transactions
    WHERE DATE(created_at) = target_date;

    IF total_cu > 0 THEN
        cu_rate := user_pool / total_cu;
    ELSE
        cu_rate := 0;
    END IF;

    INSERT INTO daily_revenue_pools(
        pool_date,
        total_revenue,
        platform_share,
        user_pool,
        total_cu,
        cu_rate
    )
    VALUES(
        target_date,
        total_rev,
        platform_share,
        user_pool,
        total_cu,
        cu_rate
    )
    ON CONFLICT (pool_date) DO UPDATE SET
        total_revenue = EXCLUDED.total_revenue,
        platform_share = EXCLUDED.platform_share,
        user_pool = EXCLUDED.user_pool,
        total_cu = EXCLUDED.total_cu,
        cu_rate = EXCLUDED.cu_rate;

    -- 3. Distribute to users
    DELETE FROM user_settlements WHERE pool_date = target_date;

    INSERT INTO user_settlements(pool_date, user_id, cu_earned, usd_allocated)
    SELECT
        target_date,
        user_id,
        SUM(cu_amount),
        SUM(cu_amount) * cu_rate
    FROM cu_transactions
    WHERE DATE(created_at) = target_date
    GROUP BY user_id;

END;
$$ LANGUAGE plpgsql;
