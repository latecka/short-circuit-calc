import { BaseEdge, EdgeLabelRenderer, getBezierPath } from 'reactflow';

export default function BreakerEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isClosed = data?.isClosed !== false;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: isClosed ? '#2563eb' : '#dc2626',
          strokeWidth: 2,
          strokeDasharray: isClosed ? '0' : '6 4',
          opacity: isClosed ? 1 : 0.3,
        }}
      />
      <EdgeLabelRenderer>
        <button
          type="button"
          onClick={() => data?.onToggle?.(data?.breakerKey)}
          disabled={!data?.interactive}
          className={`absolute w-3 h-3 -translate-x-1/2 -translate-y-1/2 border flex items-center justify-center ${
            isClosed
              ? 'bg-green-500 border-green-600'
              : 'bg-white border-red-600 text-red-600'
          } ${data?.interactive ? 'cursor-pointer' : 'cursor-default'}`}
          style={{
            left: labelX,
            top: labelY,
          }}
          title={isClosed ? 'Vypínač zatvorený' : 'Vypínač otvorený'}
        >
          {!isClosed && <span className="text-[9px] leading-none font-bold">×</span>}
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
