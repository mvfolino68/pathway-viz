import { useEffect, useRef } from "react";

interface PathwayVizWidgetProps {
  widgetId: string;
  serverUrl?: string;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * PathwayViz Widget Component for React
 *
 * Embeds a real-time PathwayViz widget via iframe.
 *
 * @example
 * ```tsx
 * <PathwayVizWidget widgetId="revenue" className="h-32 w-full" />
 * ```
 */
export function PathwayVizWidget({
  widgetId,
  serverUrl = "http://localhost:3000",
  className = "",
  style,
}: PathwayVizWidgetProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const handleError = () => {
      console.warn(`PathwayViz widget "${widgetId}" failed to load`);
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
      title={`PathwayViz ${widgetId}`}
    />
  );
}
