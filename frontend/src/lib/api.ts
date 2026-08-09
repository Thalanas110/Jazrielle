import { useMutation, useQuery } from '@tanstack/react-query';
import { isTauriRuntime } from './tauri-window';

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_URL ?? (isTauriRuntime() ? 'http://127.0.0.1:8000/api' : '/api');
}

async function commandError(response: Response): Promise<Error> {
  try {
    const payload = (await response.json()) as {
      detail?: { message?: string } | string;
    };
    const detail = payload.detail;
    const message = typeof detail === 'string' ? detail : detail?.message;
    if (message) return new Error(message);
  } catch {
    // Use the status fallback below when the response is not JSON.
  }
  return new Error(`Command request failed: ${response.status}`);
}

export interface Capability {
  id: string;
  label: string;
  description: string;
  examples: string[];
}

export interface JarvisCapabilities {
  assistant: string;
  localMode: boolean;
  llmConfigured: boolean;
  capabilities: Capability[];
}

export interface CommandResult {
  message: string;
  handled: boolean;
  app?: string | null;
  launchUrl?: string | null;
}

export interface InferenceResult {
  model?: string;
  response: string;
}

export function getGetJarvisCapabilitiesQueryKey(): readonly unknown[] {
  return ['jarvis', 'capabilities'];
}

export function useGetJarvisCapabilities({
  query,
}: {
  query: { queryKey: readonly unknown[] };
}) {
  return useQuery({
    queryKey: query.queryKey,
    queryFn: async () => {
      const response = await fetch(`${getApiBaseUrl()}/jarvis/capabilities`);
      if (!response.ok) {
        throw new Error(`Capabilities request failed: ${response.status}`);
      }
      return (await response.json()) as JarvisCapabilities;
    },
  });
}

export function useExecuteJarvisCommand() {
  return useMutation({
    mutationFn: async ({
      data,
    }: {
      data: { command: string };
    }): Promise<CommandResult> => {
      const response = await fetch(`${getApiBaseUrl()}/jarvis/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw await commandError(response);
      }
      return (await response.json()) as CommandResult;
    },
  });
}

export function useRunJarvisInference() {
  return useMutation({
    mutationFn: async ({
      data,
    }: {
      data: { prompt: string; system: string };
    }): Promise<InferenceResult> => {
      const response = await fetch(`${getApiBaseUrl()}/jarvis/inference`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error(`Inference request failed: ${response.status}`);
      }
      return (await response.json()) as InferenceResult;
    },
  });
}
