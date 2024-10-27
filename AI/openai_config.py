class OpenAIConfig:
    gpt_sufix = "Use a required format so that your answer can be parsed"
    gpt_prefix = (
        'Answer short and useful. Use json format {"text": "your_answer", "image": "your prompt for arisen picture"}')
    gpt_model_name = "gpt-4o-mini"
    gpt_temperature = 0.4
    gpt_max_tokens = 1000

    dalle_model = "dall-e-3"
    dalle_resolution = '1024x1024'
    dalle_prefix = "use the style of a color book fashion illustration.\n"
    dalle_sufix = "\ndoes not contain text."
