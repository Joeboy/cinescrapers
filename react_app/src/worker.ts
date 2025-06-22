/// <reference types="@cloudflare/workers-types" />
export interface Env {
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return await env.ASSETS.fetch(request);
  },
};
