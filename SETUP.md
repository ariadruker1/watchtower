# Setup Instructions

## 1. Create `.env` File

```bash
cp .env.example .env
```

## 2. Add Your Anthropic API Key

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

Get key: https://console.anthropic.com/account/keys

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run Demo

```bash
# Detailed step-through with agent reasoning
python step_through_demo.py

# OR simple demo with approval prompts only
python run_demo.py
```

## Security

- **Never commit `.env`** (in `.gitignore`)
- **Keep `sk-ant-...` key private**
- **Use `.env.example`** to document needed keys (without values)

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Anthropic API key not found" | Check `.env` exists in root directory |
| "Invalid API key" | Verify at https://console.anthropic.com/account/keys |
| "No module named anthropic" | Run `pip install -r requirements.txt` |

## Cost

Claude 3.5 Haiku pricing (estimate):
- **$0.0008 per incident** (~10,000 incidents per $8)
- Monitor usage: https://console.anthropic.com/account/usage
