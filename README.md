public static List<string> ExtractRolesFromJson(string json)
{
    JObject parsed = JObject.Parse(json);
    return parsed["roleData"]?["roles"]
                ?.Select(r => r["role"]?.ToString())
                .Where(r => !string.IsNullOrEmpty(r))
                .ToList() ?? new List<string>();
}