import { useEffect, useRef } from "react";

interface StreamVizWidgetProps {
  widgetId: string;
  serverUrl?: string;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * StreamViz Widget Component for React
 *
 * Embeds a real-time StreamViz widget via iframe.
 *
 * @example
 * ```tsx
 * <StreamVizWidget widgetId="revenue" className="h-32 w-full" />
 * ```
 */
export function StreamVizWidget({
  widgetId,
  serverUrl = "http://localhost:3000",
  className = "",
  style,
}: StreamVizWidgetProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const handleError = () => {
      console.warn(`StreamViz widget "${widgetId}" failed to load`);
    };

    iframe.addEventListener("error", handleError);
    return () => iframe.removeEventListener("error", handleError);
  }, [widgetId]);

  return (
    <iframe
      ref={iframeRef}
      src={`${serverUrl}/embed/${widgetId}`}
      className={className}
      style={{
        border: "none",
        width: "100%",
        height: "100%",
        ...style,
      }}
      title={`StreamViz ${widgetId}`}
    />
  );
}
