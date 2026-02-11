"use client";

import { useEffect, useCallback } from "react";
import { Separator } from "react-resizable-panels";

interface ResizeHandleProps {
  onDragging?: (isDragging: boolean) => void;
}

export function ResizeHandle({ onDragging }: ResizeHandleProps) {
  const handlePointerDown = useCallback(() => {
    onDragging?.(true);
  }, [onDragging]);

  // Use global pointerup to ensure we always clear dragging state
  // even if the pointer is released outside the handle
  useEffect(() => {
    if (!onDragging) return;
    const handlePointerUp = () => onDragging(false);
    window.addEventListener("pointerup", handlePointerUp);
    return () => window.removeEventListener("pointerup", handlePointerUp);
  }, [onDragging]);

  return (
    <Separator
      className="group relative w-2 flex items-center justify-center data-[resize-handle-active]:bg-blue-500/10"
      onPointerDown={handlePointerDown}
    >
      {/* Visible line */}
      <div className="w-px h-full bg-zinc-800 group-hover:w-[3px] group-hover:bg-blue-500/50 group-data-[resize-handle-active]:w-[3px] group-data-[resize-handle-active]:bg-blue-500 transition-all duration-150 rounded-full" />
    </Separator>
  );
}
