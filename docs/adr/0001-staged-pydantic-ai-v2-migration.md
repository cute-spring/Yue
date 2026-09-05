# Stage the Pydantic AI V2 migration through the latest V1 release

Yue will first upgrade from Pydantic AI 1.63.0 to 1.107.4 and resolve all deprecation warnings, then migrate to pinned Pydantic AI 2.37.0. This lowers the risk of combining V1 API removals with V2 behavioral changes across the chat execution boundary and tool runtime.

