var content = await response.Content.ReadAsStringAsync();

if (string.IsNullOrWhiteSpace(content))
    return new List<string>();

var json = JObject.Parse(content);
var roles = json["roledata"]?["roles"] as JArray;

return roles?
    .Select(r => r?.ToString())
    .Where(r => !string.IsNullOrEmpty(r))
    .ToList() ?? new List<string>();