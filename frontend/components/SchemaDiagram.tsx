"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  Handle,
  MarkerType,
  type Node,
  type NodeMouseHandler,
  type NodeProps,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import dagre from "dagre";
import { KeyRound, Link2, X } from "lucide-react";

import "@xyflow/react/dist/style.css";

import type { SchemaTable } from "@/lib/types";

/* ------------------------------------------------------------------ */
/*  Context — lets TableNodeView dispatch "insert column" without      */
/*  prop-drilling through React Flow's data shape                       */
/* ------------------------------------------------------------------ */

interface SchemaActions {
  insertColumn: (tableName: string, columnName: string) => void;
}
const SchemaActionsContext = createContext<SchemaActions | null>(null);

/* ------------------------------------------------------------------ */
/*  Custom TableNode — matches the Console palette                     */
/* ------------------------------------------------------------------ */

const ROW_HEIGHT = 26;
const HEADER_HEIGHT = 44;
const NODE_WIDTH = 240;

type TableNodeData = {
  table: SchemaTable;
};

type TableNode = Node<TableNodeData, "table">;

function TableNodeView({ data }: NodeProps<TableNode>) {
  const { table } = data;
  const actions = useContext(SchemaActionsContext);
  const fkByCol = new Map(table.foreign_keys.map((fk) => [fk.from_col, fk]));
  const pkSet = new Set(table.columns.filter((c) => c.pk).map((c) => c.name));

  return (
    <div
      className="rounded-lg border border-white/[0.08] bg-zinc-900/95 shadow-2xl
                 backdrop-blur-sm overflow-hidden"
      style={{ width: NODE_WIDTH }}
    >
      {/* Header */}
      <div
        className="px-3.5 flex items-center justify-between bg-zinc-800/80
                   border-b border-white/[0.08]"
        style={{ height: HEADER_HEIGHT }}
      >
        <span className="text-zinc-100 text-[13.5px] font-medium tracking-tight truncate">
          {table.name}
        </span>
        <span className="text-[9px] font-mono tracking-[0.16em] uppercase text-zinc-500 ml-2 flex-shrink-0">
          {table.row_count.toLocaleString()}
        </span>
      </div>

      {/* Columns */}
      <div className="py-1">
        {table.columns.map((c) => {
          const isPk = pkSet.has(c.name);
          const isFk = fkByCol.has(c.name);
          return (
            <div
              key={c.name}
              role="button"
              tabIndex={0}
              onPointerDown={(e) => {
                // Stop drag from starting when the user is clicking a column to insert it.
                e.stopPropagation();
              }}
              onClick={(e) => {
                e.stopPropagation();
                actions?.insertColumn(table.name, c.name);
              }}
              className="relative flex items-center gap-2 px-3.5 text-[11.5px] font-mono
                         cursor-pointer hover:bg-accent/[0.08] transition-colors"
              style={{ height: ROW_HEIGHT }}
              title={`Insert ${table.name}.${c.name} into composer`}
            >
              {/* Inbound handle (left) — referenced when this col is a PK */}
              <Handle
                type="target"
                position={Position.Left}
                id={`${c.name}-in`}
                isConnectable={false}
                style={{
                  background: "transparent",
                  border: "none",
                  width: 6,
                  height: 6,
                  left: -3,
                  pointerEvents: "none",
                }}
              />

              {/* Icon */}
              {isPk ? (
                <KeyRound
                  className="w-2.5 h-2.5 text-accent flex-shrink-0"
                  strokeWidth={2}
                />
              ) : isFk ? (
                <Link2
                  className="w-2.5 h-2.5 text-zinc-400 flex-shrink-0"
                  strokeWidth={2}
                />
              ) : (
                <span className="w-2.5 inline-block flex-shrink-0" />
              )}

              {/* Name */}
              <span
                className={`flex-1 truncate ${
                  isPk
                    ? "text-accent"
                    : isFk
                      ? "text-zinc-200"
                      : "text-zinc-300"
                }`}
              >
                {c.name}
              </span>

              {/* Type */}
              <span className="text-zinc-500 text-[9.5px] uppercase tracking-wide flex-shrink-0">
                {c.type.toLowerCase()}
              </span>

              {/* Outbound handle (right) — used when this col is a FK */}
              <Handle
                type="source"
                position={Position.Right}
                id={`${c.name}-out`}
                isConnectable={false}
                style={{
                  background: "transparent",
                  border: "none",
                  width: 6,
                  height: 6,
                  right: -3,
                  pointerEvents: "none",
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

const nodeTypes = { table: TableNodeView };

/* ------------------------------------------------------------------ */
/*  Layout — dagre auto-positions nodes left-to-right                  */
/* ------------------------------------------------------------------ */

function layoutTables(tables: SchemaTable[]): {
  nodes: TableNode[];
  edges: Edge[];
} {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "LR",
    nodesep: 60,
    ranksep: 140,
    marginx: 40,
    marginy: 40,
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes
  for (const t of tables) {
    const height = HEADER_HEIGHT + t.columns.length * ROW_HEIGHT + 8;
    g.setNode(t.name, { width: NODE_WIDTH, height });
  }

  // Add edges (foreign keys)
  const edges: Edge[] = [];
  for (const t of tables) {
    for (const fk of t.foreign_keys) {
      // Skip self-referential edges in layout — they'd confuse dagre
      // (we still render them as a small loop on the node).
      g.setEdge(t.name, fk.to_table);
      edges.push({
        id: `${t.name}.${fk.from_col}->${fk.to_table}.${fk.to_col}`,
        source: t.name,
        sourceHandle: `${fk.from_col}-out`,
        target: fk.to_table,
        targetHandle: `${fk.to_col}-in`,
        type: "default", // bezier curve
        animated: true,
        style: {
          stroke: "rgba(197, 245, 0, 0.4)",
          strokeWidth: 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "rgba(197, 245, 0, 0.6)",
          width: 14,
          height: 14,
        },
      });
    }
  }

  dagre.layout(g);

  const nodes: TableNode[] = tables.map((t) => {
    const pos = g.node(t.name);
    return {
      id: t.name,
      type: "table",
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - pos.height / 2 },
      data: { table: t },
      draggable: true,
    };
  });

  return { nodes, edges };
}

/* ------------------------------------------------------------------ */
/*  Modal wrapper                                                      */
/* ------------------------------------------------------------------ */

interface SchemaDiagramProps {
  databaseName: string;
  tables: SchemaTable[];
  onClose: () => void;
  /** Called when the user clicks a column row — receives `Table.Column`. */
  onInsertColumn?: (snippet: string) => void;
}

export default function SchemaDiagram({
  databaseName,
  tables,
  onClose,
  onInsertColumn,
}: SchemaDiagramProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const actions = useMemo<SchemaActions>(
    () => ({
      insertColumn: (tableName, columnName) => {
        onInsertColumn?.(`${tableName}.${columnName}`);
        onClose();
      },
    }),
    [onInsertColumn, onClose],
  );

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const initial = useMemo(() => layoutTables(tables), [tables]);

  // Stateful node/edge stores — required for drag to actually update positions.
  const [baseNodes, , onNodesChange] = useNodesState<TableNode>(initial.nodes);
  const [baseEdges, , onEdgesChange] = useEdgesState<Edge>(initial.edges);

  // Build a map of which tables are connected to which (via any FK direction)
  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const t of tables) m.set(t.name, new Set());
    for (const e of baseEdges) {
      m.get(e.source)?.add(e.target);
      m.get(e.target)?.add(e.source);
    }
    return m;
  }, [tables, baseEdges]);

  // Apply highlight styling to nodes + edges based on `selected`. The base
  // store keeps drag-updated positions; we just decorate visually.
  const nodes = useMemo(() => {
    if (!selected) return baseNodes;
    const related = neighbors.get(selected) ?? new Set();
    return baseNodes.map((n) => {
      const isFocus = n.id === selected;
      const isRelated = related.has(n.id);
      const dimmed = !isFocus && !isRelated;
      return {
        ...n,
        style: {
          ...n.style,
          opacity: dimmed ? 0.25 : 1,
          transition: "opacity 200ms ease-out",
          filter: isFocus
            ? "drop-shadow(0 0 24px rgba(197,245,0,0.45))"
            : undefined,
        },
      };
    });
  }, [baseNodes, selected, neighbors]);

  const edges = useMemo(() => {
    if (!selected) return baseEdges;
    return baseEdges.map((e) => {
      const isRelated = e.source === selected || e.target === selected;
      return {
        ...e,
        animated: isRelated,
        style: {
          ...e.style,
          stroke: isRelated ? "#c5f500" : "rgba(255,255,255,0.06)",
          strokeWidth: isRelated ? 2.5 : 1,
          opacity: isRelated ? 1 : 0.5,
          transition: "stroke 200ms, opacity 200ms",
        },
        markerEnd: isRelated
          ? {
              type: MarkerType.ArrowClosed,
              color: "#c5f500",
              width: 16,
              height: 16,
            }
          : {
              type: MarkerType.ArrowClosed,
              color: "rgba(255,255,255,0.1)",
              width: 12,
              height: 12,
            },
      };
    });
  }, [baseEdges, selected]);

  const onNodeClick = useCallback<NodeMouseHandler>((_, node) => {
    setSelected((prev) => (prev === node.id ? null : node.id));
  }, []);

  const onPaneClick = useCallback(() => setSelected(null), []);

  const fkCount = useMemo(
    () => tables.reduce((acc, t) => acc + t.foreign_keys.length, 0),
    [tables],
  );

  return (
    <SchemaActionsContext.Provider value={actions}>
    <div className="fixed inset-0 z-50 flex flex-col bg-zinc-950/95 backdrop-blur-md">
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div>
          <p className="eyebrow-accent mb-1">schema diagram</p>
          <h2 className="text-zinc-100 text-[18px] font-medium tracking-tight">
            {databaseName}
            <span className="text-zinc-500 text-[13px] font-mono ml-3">
              {tables.length} tables · {fkCount} relationships
            </span>
          </h2>
        </div>
        <button
          onClick={onClose}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-white/[0.1]
                     text-[11px] font-mono tracking-[0.18em] uppercase text-zinc-400
                     hover:text-zinc-100 hover:border-white/[0.2] transition-colors"
          aria-label="Close diagram"
        >
          close
          <X className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>
      </header>

      <div className="flex-1 min-h-0">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.2}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
            colorMode="dark"
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="rgba(255, 255, 255, 0.06)"
            />
            <Controls
              showInteractive={false}
              style={{
                background: "rgba(24, 24, 27, 0.95)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: 6,
              }}
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      <footer className="px-6 py-2.5 border-t border-white/[0.06] flex items-center gap-6 text-[10px] font-mono tracking-[0.16em] uppercase text-zinc-500">
        <span className="flex items-center gap-1.5">
          <KeyRound className="w-3 h-3 text-accent" strokeWidth={2} /> primary key
        </span>
        <span className="flex items-center gap-1.5">
          <Link2 className="w-3 h-3 text-zinc-400" strokeWidth={2} /> foreign key
        </span>
        <span className="ml-auto text-zinc-600">
          click column to insert · click table header to focus · drag to rearrange · scroll to zoom
        </span>
      </footer>
    </div>
    </SchemaActionsContext.Provider>
  );
}
