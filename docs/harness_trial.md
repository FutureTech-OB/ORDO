# DeepSeek Harness research-assistant trial

The official @deepseek-ai/dsh 0.2.0-rc.2 host connects to ORDO's MCP tools through a compatible gateway using deepseek-v4.1-flash. The assistant plans, previews, starts and inspects an experiment; the simulation uses free rules. Two worlds contain eight employees, two departments and three rounds, comparing siloed and bridge contacts at seed 7.

The host completes nine model steps and eight tool calls in 59.29 seconds. The simulation makes 48 rule choices with zero model-service requests. Final performance is 20.092370 for siloed contacts and 30.837850 for bridges; exploration rates are 0.500 and 0.375. All six period metrics match replay, and inspection retrieves the actual world-0, round-2, agent-0 explore event.

Host usage is 9,225 uncached input, 25,216 cached input and 1,542 output tokens, totaling 35,983. Bounded waiting was added after repeated status polling, with a default of 10 seconds and maximum 15. The research assistant and simulation engine use separate credentials and responsibilities.

## Configuration and execution

| Contact condition | Final per-member solution performance `gross_performance` | Whole-run mean exploration share |
| --- | --- | --- |
| siloed | 20.092370 | 0.500 |
| bridge | 30.837850 | 0.375 |

## Sources and records

- [Source repository](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/bundle/headless)
- [Source repository](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/llm/llm-pi-ai)
- [Source repository](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/mcp/mcp-client)
