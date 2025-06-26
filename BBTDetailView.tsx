internal static async Task<List<string>> GetAsJsonRolesAsync(this HttpClient client, Uri relativeUri, CancellationToken token)
{
    var response = await client.GetAsync(relativeUri, token);
    response.EnsureSuccessStatusCode();

    var content = await response.Content.ReadAsStringAsync();
    return JArray.Parse(content)
                 .Select(role => role?.ToString())
                 .Where(role => !string.IsNullOrEmpty(role))
                 .ToList();
}