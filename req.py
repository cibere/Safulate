# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
# ]
# ///
print(
    __import__("json").dumps(
        dict(
            __import__("requests")
            .get(
                "https://github.com/cibere/Rtfm-Indexes/raw/refs/heads/indexes-v2/indexes_v2/api.emberjs.com-3.28.cidex"
            )
            .headers
        ),
        indent=4,
    )
)
