# Model Card

## Reflection

**Limitations and biases**

The dataset only has 120 songs, so the system is pretty limited in range. If you ask for something niche there's a good chance nothing in the dataset fits well and the recommendations will feel off. The genre and mood families are also hand-coded, which means they reflect my own assumptions about what genres are "related." Someone else might draw those lines differently.

The scoring weights (genre 28%, mood 24%, etc.) were also set by feel, not by any data-driven process. They work okay but there's no real reason genre should be worth exactly 28%, it just seemed right at the time.

**Could it be misused?**

Honestly, it's a music recommender, so the risk is pretty low compared to most AI systems. The main concern I can think of is API key exposure because if someone got hold of your Groq key they could rack up usage under your account. That's already handled by keeping the key in `.env` and out of version control. Beyond that, there's not much harmful you could do with a music recommender.

**What surprised me during testing**

I expected the guardrail to catch actual hallucinations where the LLM made up songs that don't exist. What I didn't expect was it triggering because the LLM was wrapping song titles in quotes (`"Tokyo Cafe"` instead of `Tokyo Cafe`). Technically correct output, but it broke the string matching completely. It was a good reminder that "the AI gave the right answer" and "the system handled the answer correctly" are two different problems.

The other surprise was how inconsistent the output format was. The same prompt would sometimes use an em-dash (`—`) and sometimes a regular hyphen (`-`) to separate the song title from the artist. Small thing, but it kept breaking the parser until the prompt was made more explicit about it.

**Collaboration with AI**

I used Claude throughout this project, for writing code, debugging errors, and helping structure the system.

One genuinely helpful moment was when Gemini kept hitting quota limits and I wasn't sure whether it was the model, the key, or the account. Claude diagnosed that the `limit: 0` in the error meant the entire free tier quota was exhausted at the account level, not just one model which meant switching models wouldn't help. That saved me from going in circles trying different Gemini models. It also suggested Groq as a free alternative, which ended up working perfectly.

One moment where it went wrong: Claude wrote the initial title extraction logic to split on `—` (em-dash) as the separator between song title and artist. That worked in the first test but failed randomly after that because the LLM sometimes used a regular hyphen instead. Claude hadn't accounted for that inconsistency, and it took a few rounds of debugging to track it down and fix properly. It's the kind of thing that's easy to miss when you're generating code without running it.
