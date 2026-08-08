import { useMutation, useQuery } from '@tanstack/react-query';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

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
      const response = await fetch(`${API_BASE}/jarvis/capabilities`);
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
      const response = await fetch(`${API_BASE}/jarvis/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error(`Command request failed: ${response.status}`);
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
      const response = await fetch(`${API_BASE}/jarvis/inference`, {
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
