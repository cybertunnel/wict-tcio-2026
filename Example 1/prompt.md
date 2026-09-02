# Prompt for Example 1

Paste below into the agent prompt

> In `./base application/` Add rate limiting to the API and make sure it works

**The Issue**
The prompt used doesn't say which endpoint, so it assumed `/hello` should be rate limited. However, our goal might have been to have ALL endpoints rate limited.