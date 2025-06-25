public static class OracleHelper
{
    public static void DropTableIfExists(string tableName, string connStr)
    {
        using (var conn = new OracleConnection(connStr))
        {
            conn.Open();
            var cmd = conn.CreateCommand();
            cmd.CommandText = $@"
                BEGIN
                    EXECUTE IMMEDIATE 'DROP TABLE {tableName}';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -942 THEN
                            RAISE;
                        END IF;
                END;";
            cmd.ExecuteNonQuery();
        }
    }

    public static void CreateTableFromMaster(string csvPath, string tableName, string connStr)
    {
        // Read headers and generate create table statement
        var headers = File.ReadLines(csvPath).First().Split(',');
        var columns = headers.Select(h => $"{h.Trim().ToUpper()} VARCHAR2(4000)").ToArray();
        var createTableSQL = $"CREATE TABLE {tableName} ({string.Join(",", columns)})";

        using (var conn = new OracleConnection(connStr))
        {
            conn.Open();
            var cmd = conn.CreateCommand();
            cmd.CommandText = createTableSQL;
            cmd.ExecuteNonQuery();
        }
    }

    public static void InsertDataFromCsv(string csvPath, string tableName, string connStr)
    {
        // Basic line-by-line insert
        var lines = File.ReadAllLines(csvPath).Skip(1); // Skip headers

        using (var conn = new OracleConnection(connStr))
        {
            conn.Open();
            foreach (var line in lines)
            {
                var values = line.Split(',').Select(v => $"'{v.Replace("'", "''")}'").ToArray();
                var insertSQL = $"INSERT INTO {tableName} VALUES ({string.Join(",", values)})";

                var cmd = conn.CreateCommand();
                cmd.CommandText = insertSQL;
                cmd.ExecuteNonQuery();
            }
        }
    }

    public static void ApplyDeltaChanges(string deltaPath, string tableName, string connStr)
    {
        var lines = File.ReadAllLines(deltaPath).Skip(1); // Assuming first line is header
        using (var conn = new OracleConnection(connStr))
        {
            conn.Open();
            foreach (var line in lines)
            {
                var cols = line.Split(',');

                var action = cols[0]; // e.g., "APPEND", "UPDATE", "DELETE"
                var keyColumn = "ID"; // Replace with actual key column name
                var keyValue = cols[1];

                if (action == "APPEND")
                {
                    var values = cols.Skip(1).Select(v => $"'{v.Replace("'", "''")}'").ToArray();
                    var insertSQL = $"INSERT INTO {tableName} VALUES ({string.Join(",", values)})";
                    var cmd = conn.CreateCommand();
                    cmd.CommandText = insertSQL;
                    cmd.ExecuteNonQuery();
                }
                else if (action == "UPDATE")
                {
                    var setClause = string.Join(",", cols.Skip(2).Select((v, i) => $"COL{i+2}='{v}'")); // Adjust column names
                    var updateSQL = $"UPDATE {tableName} SET {setClause} WHERE {keyColumn} = '{keyValue}'";
                    var cmd = conn.CreateCommand();
                    cmd.CommandText = updateSQL;
                    cmd.ExecuteNonQuery();
                }
                else if (action == "DELETE")
                {
                    var deleteSQL = $"DELETE FROM {tableName} WHERE {keyColumn} = '{keyValue}'";
                    var cmd = conn.CreateCommand();
                    cmd.CommandText = deleteSQL;
                    cmd.ExecuteNonQuery();
                }
            }
        }
    }
}