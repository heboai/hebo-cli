# hebo-cli

## Installation

```
pip install hebo-cli
```

## Usage

### To configure your profile

```
hebo config
```

### To download remote knowledge and congiguration

```
hebo pull agent-name [-p profile-name]
```

### To add a MCP client configuration

```
hebo add mcp-config agent-name
```

### To update remote knowledge and configuration with local files

```
hebo push agent-name [-p profile-name]
```

## Contributing

```
uv sync
source .venv/bin/activate
```