import { toPng } from 'html-to-image';

export async function exportSchemaToBase64(containerElement) {
  return await toPng(containerElement, {
    filter: (node) => {
      const className = node.className || '';
      if (typeof className === 'string') {
        return !className.includes('react-flow__controls') &&
               !className.includes('react-flow__minimap');
      }
      return true;
    },
    backgroundColor: '#ffffff',
    pixelRatio: 2
  });
}
