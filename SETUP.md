# Setup Instructions

## 1. Create `.env` File

Copy the template file:
```bash
cp .env.example .env
```

## 2. Add Your OpenAI API Key

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Get your key from: https://platform.openai.com/api-keys

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Demo

```bash
python run_demo.py
```

## Security Notes

- **Never commit `.env`** - it's in `.gitignore` and contains secrets
- **Keep `sk-...` key private** - treat it like a password
- **Use `.env.example`** to show what config keys are needed (without values)

## Troubleshooting

**"OpenAI API key not found"**
- Check that `.env` file exists in same directory as `run_demo.py`
- Verify `OPENAI_API_KEY=sk-...` is in `.env`
- No quotes needed around the API key

**"Invalid API key"**
- Verify key from https://platform.openai.com/api-keys
- Make sure it's not truncated or has extra whitespace
- Check that key starts with `sk-`

**Import error: "No module named dotenv"**
```bash
pip install python-dotenv
```

## Cost Estimation

With GPT-3.5-turbo at $0.5 per 1M input + $1.5 per 1M output tokens:

- **$10**: ~15,000-20,000 incidents
- **$1**: ~1,500-2,000 incidents
- **~$0.0005 per incident**

Monitor usage at: https://platform.openai.com/account/billing/usage
