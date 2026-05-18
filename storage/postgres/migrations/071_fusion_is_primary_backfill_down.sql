-- B293 (v0.10.0.2): down is intentionally a no-op. We can't safely
-- distinguish backfilled is_primary flags from operator-set ones once
-- the UI has been used. Rolling back the up-migration would risk
-- clearing operator intent. The post-B293 _get_primary_widget guard
-- still works correctly with the backfill in place under any code
-- version, so leaving it applied is safe.

SELECT 1;
