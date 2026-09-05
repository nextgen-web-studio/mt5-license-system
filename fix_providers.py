with open("frontend/src/app/providers.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Increase gcTime too so data stays in cache even when switching sections
content = content.replace(
    "staleTime: 5 * 60 * 1000, // 5 minutes lightning fast cache",
    "staleTime: 5 * 60 * 1000,    // 5 minutes - data considered fresh, no refetch\n        gcTime: 10 * 60 * 1000,       // 10 minutes - keep data in memory after unused\n        retry: 2,                       // Retry failed requests twice\n        retryDelay: 500,                // Fast 500ms retry"
)

with open("frontend/src/app/providers.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated React Query config")
