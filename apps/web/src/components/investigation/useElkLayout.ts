import { useCallback } from "react";
import ELK from "elkjs/lib/elk.bundled.js";
import type { Node, Edge } from "@xyflow/react";

const elk = new ELK();

const ELK_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "DOWN",
  "elk.spacing.nodeNode": "80",
  "elk.layered.spacing.nodeNodeBetweenLayers": "100",
  "elk.layered.spacing.edgeNodeBetweenLayers": "40",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
  "elk.edgeRouting": "SPLINES",
  "elk.padding": "[top=50,left=50,bottom=50,right=50]",
};

export function useElkLayout() {
  const computeLayout = useCallback(
    async (
      nodes: Node[],
      edges: Edge[],
    ): Promise<{ nodes: Node[]; edges: Edge[] }> => {
      const elkGraph = {
        id: "root",
        layoutOptions: ELK_OPTIONS,
        children: nodes.map((node) => ({
          id: node.id,
          width: node.measured?.width ?? (node.data.nodeType === "person" ? 180 : 200),
          height: node.measured?.height ?? (node.data.nodeType === "person" ? 60 : 72),
        })),
        edges: edges.map((edge) => ({
          id: edge.id,
          sources: [edge.source],
          targets: [edge.target],
        })),
      };

      const layout = await elk.layout(elkGraph);

      const layoutNodes = nodes.map((node) => {
        const elkNode = layout.children?.find((n) => n.id === node.id);
        return {
          ...node,
          position: {
            x: elkNode?.x ?? 0,
            y: elkNode?.y ?? 0,
          },
        };
      });

      return { nodes: layoutNodes, edges };
    },
    [],
  );

  return { computeLayout };
}
