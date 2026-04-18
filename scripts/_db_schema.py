import psycopg2

conn = psycopg2.connect("postgresql://postgres:UeQPgBPldwyXoAjyEySkyYKEvXdOglxo@metro.proxy.rlwy.net:48417/railway")
with conn.cursor() as cur:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'execution_logs'")
    print("Execution Logs Columns:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
    
    print("\nWorkflows Columns:")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'workflows'")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
