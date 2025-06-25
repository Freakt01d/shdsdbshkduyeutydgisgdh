public static List<string> GetAndParseJsonResultForRoles(string url)
{
    using (HttpClient httpClient = new HttpClient())
    {
        string json = httpClient.GetStringAsync(url).Result;

        JObject parsed = JObject.Parse(json);
        List<string> roleStrings = parsed["roleData"]?["roles"]
            ?.Select(r => r["role"]?.ToString())
            .Where(r => !string.IsNullOrEmpty(r))
            .ToList() ?? new List<string>();

        return roleStrings;
    }
}