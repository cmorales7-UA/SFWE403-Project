from backend.clients import database


def ensure_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS reviewer_recommendations (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            recommendation TEXT NOT NULL
                CHECK (recommendation IN ('recommend', 'deny', 'defer')),
            comments TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(application_id, reviewer_id)
        )
    """)


def get_recommendation(application_id, reviewer_id):
    with database.connect() as db:
        ensure_table(db)

        row = db.execute(
            """
            SELECT * FROM reviewer_recommendations
            WHERE application_id = ? AND reviewer_id = ?
            """,
            (application_id, reviewer_id),
        ).fetchone()

        return dict(row) if row else None


def save_recommendation(
    application_id,
    reviewer_id,
    recommendation,
    comments,
):
    with database.connect() as db:
        ensure_table(db)

        db.execute(
            """
            INSERT INTO reviewer_recommendations (
                application_id, reviewer_id, recommendation, comments
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(application_id, reviewer_id)
            DO UPDATE SET
                recommendation = excluded.recommendation,
                comments = excluded.comments,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                application_id,
                reviewer_id,
                recommendation,
                comments,
            ),
        )

    return get_recommendation(application_id, reviewer_id)


def list_recommendations(reviewer_id):
    with database.connect() as db:
        ensure_table(db)

        return [
            dict(row)
            for row in db.execute(
                """
                SELECT * FROM reviewer_recommendations
                WHERE reviewer_id = ?
                ORDER BY application_id
                """,
                (reviewer_id,),
            )
        ]