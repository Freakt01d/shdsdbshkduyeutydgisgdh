using (var conn = new OracleConnection(_reddDbConnStr))
{
    conn.Open();

    if (toInsert.Any())
    {
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = "INSERT INTO TraceFiles (cusip) VALUES (:cusip)";
            cmd.ArrayBindCount = toInsert.Count;
            cmd.Parameters.Add("cusip", OracleDbType.Varchar2, toInsert.ToArray(), ParameterDirection.Input);
            cmd.ExecuteNonQuery();
        }
    }

    if (toDelete.Any())
    {
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = "DELETE FROM TraceFiles WHERE cusipid = :cusip";
            cmd.ArrayBindCount = toDelete.Count;
            cmd.Parameters.Add("cusip", OracleDbType.Varchar2, toDelete.ToArray(), ParameterDirection.Input);
            cmd.ExecuteNonQuery();
        }
    }

    _logger.Info($"Inserted: {toInsert.Count}, Deleted: {toDelete.Count} for date {partitionDate:yyyy-MM-dd}");
}