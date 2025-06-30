internal static CatReportDataApi[] GetAndParseCatReportFlatFileResult<T>(
    this HttpClient client,
    Uri relativeUri,
    CancellationToken token,
    string CatDataFilePath,
    string destinationFolderPath)
{
    if (client.Timeout != TimeSpan.FromMinutes(5))
        client.Timeout = TimeSpan.FromMinutes(5);

    var result = client.GetAsync(relativeUri, token).Result;
    using (result)
    {
        result.EnsureSuccessStatusCode();

        var resultContent = result.Content.ReadAsByteArrayAsync().Result;
        AppendAllBytes(CatDataFilePath, resultContent); // saves to disk

        // ✅ Assume this is a .txt pipe-delimited file, NOT .gz
        var lines = File.ReadAllLines(destinationFolderPath);
        if (lines.Length < 2)
            return Array.Empty<CatReportDataApi>();

        var headers = lines[0].Split('|');
        var records = new List<Dictionary<string, string>>();

        foreach (var line in lines.Skip(1))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            var values = line.Split('|');
            var record = new Dictionary<string, string>();

            for (int i = 0; i < headers.Length && i < values.Length; i++)
            {
                record[headers[i].Trim()] = values[i].Trim();
            }

            records.Add(record);
        }

        // ✅ Convert to JSON string
        var jsonData = JsonConvert.SerializeObject(records);

        // ✅ Keep your original deserialization logic intact
        return JsonConvert.DeserializeObject<CatReportDataApi[]>(jsonData);
    }
}