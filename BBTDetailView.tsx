var content = await response.Content.ReadAsStringAsync();
return JArray.Parse(content)
             .Select(role => role?["role"]?.ToString())
             .Where(role => !string.IsNullOrEmpty(role))
             .ToList();