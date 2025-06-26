var content = await response.Content.ReadAsStringAsync();
JToken parsed = JToken.Parse(content);

List<string> roles = parsed
    .Select(token => token["role"]?.ToString())
    .Where(roleName => !string.IsNullOrEmpty(roleName))
    .ToList();