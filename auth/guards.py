from fastapi import HTTPException


def _normalized_email(value: str | None) -> str:
    return (value or "").strip().lower()


def user_exists(conn, user_email: str) -> bool:
    normalized = _normalized_email(user_email)
    if not normalized:
        return False

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM users WHERE lower(email) = %s
            ) OR EXISTS (
                SELECT 1 FROM google_tokens WHERE lower(user_email) = %s
            )
            """,
            (normalized, normalized),
        )
        row = cur.fetchone()
    return bool(row and row[0])


def require_user_header(
    conn,
    x_user_email: str | None,
    *,
    claimed_user_email: str | None = None,
    require_known_user: bool = True,
) -> str:
    normalized_header = _normalized_email(x_user_email)
    normalized_claim = _normalized_email(claimed_user_email)

    if not normalized_header:
        raise HTTPException(status_code=401, detail="Missing X-User-Email header")

    if normalized_claim and normalized_header != normalized_claim:
        raise HTTPException(status_code=403, detail="Forbidden")

    if require_known_user and not user_exists(conn, normalized_header):
        raise HTTPException(status_code=403, detail="Forbidden")

    return normalized_header
