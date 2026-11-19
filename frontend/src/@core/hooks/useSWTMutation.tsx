"use client";

import { useCallback, useRef, useState } from "react";

type SWTMutationProps<SWTOutputType, SWTInputType> = {
  onSuccess?: (res: SWTOutputType | null) => void;
  onError?: (error: Error) => void;
  mutationFn: (input: SWTInputType) => Promise<SWTOutputType | null>;
};

const useSWTMutation = <SWTOutputType, SWTInputType = void>({
  mutationFn,
  onSuccess,
  onError,
}: SWTMutationProps<SWTOutputType, SWTInputType>) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isInitLoading, setIsInitLoading] = useState<boolean>(false);
  const [input, setInput] = useState<SWTInputType | null>(null);
  const [output, setOutput] = useState<SWTOutputType | null>(null);
  const [error, setError] = useState<string>("");
  const isLoaded = useRef<boolean>(false);

  const reset = useCallback(() => {
    setOutput(null);
    setError("");
  }, []);

  const mutation = useCallback(
    async (payload: SWTInputType) => {
      setIsLoading(true);
      setError("");
      if (!isLoaded.current) setIsInitLoading(true);
      try {
        const response = await mutationFn(payload);
        setOutput(response);
        setInput(payload);
        if (onSuccess) onSuccess(response);
        return response;
      } catch (err) {
        const normalized = err instanceof Error ? err : new Error("Operation failed.");
        setError(normalized.message);
        if (onError) onError(normalized);
        return null;
      } finally {
        setIsLoading(false);
        if (!isLoaded.current) {
          setIsInitLoading(false);
          isLoaded.current = true;
        }
      }
    },
    [mutationFn, onError, onSuccess],
  );

  return { mutation, isLoading, isInitLoading, input, data: output, error, setError, reset };
};

export default useSWTMutation;
