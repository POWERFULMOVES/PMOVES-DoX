'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { HyperbolicNavigator } from "../geometry/HyperbolicNavigator";
import { ZetaVisualizer } from "../geometry/ZetaVisualizer";

// Types based on A2UI Protocol v0.8
type ComponentId = string;

/**
 * Generic A2UI Component definition.
 */
interface A2UIComponent {
    [key: string]: any;
}

/**
 * Message defining the structure of the UI surface.
 */
interface SurfaceUpdate {
    surfaceId: string;
    components: { id: ComponentId, component: A2UIComponent }[];
}

/**
 * Message signaling the start of rendering for a surface.
 */
interface BeginRendering {
    surfaceId: string;
    root: ComponentId;
    catalogId?: string;
    styles?: any;
}

/**
 * Message for updating the data model bound to the UI.
 */
interface DataModelUpdate {
    surfaceId: string;
    path?: string;
    contents: any[];
}

/**
 * Props for the A2UIRenderer component.
 */
interface A2UIRendererProps {
    /** Stream of A2UI protocol messages (JSON objects) or a simple card object */
    content: any[] | any;
    /** Callback for button actions */
    onAction?: (action: any) => void;
    /** Optional CSS class name */
    className?: string;
}

// Map A2UI components to React components
const ComponentRegistry: Record<string, React.FC<any>> = {
    Text: ({ text, usageHint }) => {
        const str = text?.literalString || (text?.path ? `{{${text.path}}}` : "");
        if (usageHint === 'h1') return <h1 className="text-3xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-500">{str}</h1>;
        if (usageHint === 'h2') return <h2 className="text-2xl font-semibold mb-3 text-foreground">{str}</h2>;
        if (usageHint === 'h3') return <h3 className="text-xl font-medium mb-2 text-foreground/90">{str}</h3>;
        return <p className="text-sm text-muted-foreground leading-relaxed">{str}</p>;
    },
    
    Button: ({ label, action, onAction }) => (
        <Button 
            className="w-full sm:w-auto bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-700 shadow-lg shadow-primary/20"
            onClick={() => onAction && onAction(action)}
        >
            {label?.literalString}
        </Button>
    ),

    Card: ({ child, renderId }) => (
        <Card className="glass-card overflow-hidden border-white/10 shadow-2xl">
            <CardContent className="p-6">
                {renderId(child)}
            </CardContent>
        </Card>
    ),

    Column: ({ children, renderId }) => (
        <div className="flex flex-col gap-4">
            {children?.explicitList?.map((cid: string) => (
                <div key={cid} className="w-full">
                    {renderId(cid)}
                </div>
            ))}
        </div>
    ),

    Row: ({ children, renderId, alignment }) => (
        <div className={cn(
            "flex flex-wrap gap-4 items-center",
            alignment === 'center' ? 'justify-center' : 
            alignment === 'end' ? 'justify-end' : 'justify-start'
        )}>
            {children?.explicitList?.map((cid: string) => (
                <div key={cid}>
                    {renderId(cid)}
                </div>
            ))}
        </div>
    ),
    
    HyperbolicNavigator: ({ data, width, height, className }) => (
        <HyperbolicNavigator 
            data={data}
            width={width}
            height={height}
            className={className}
        />
    ),

    ZetaVisualizer: ({ frequencies, amplitudes, width, height, className }) => (
        <ZetaVisualizer 
            frequencies={frequencies}
            amplitudes={amplitudes}
            width={width}
            height={height}
            className={className}
        />
    )
};

/**
 * Renders simple card-style content (fallback for non-protocol payloads)
 */
function SimpleCardRenderer({ content }: { content: any }) {
    if (!content) return null;

    return (
        <Card className="glass-card overflow-hidden border-white/10">
            <CardHeader className="pb-2">
                {content.title && (
                    <CardTitle className="text-lg">{content.title}</CardTitle>
                )}
                {content.description && (
                    <CardDescription>{content.description}</CardDescription>
                )}
            </CardHeader>
            {(content.items || content.text || content.data) && (
                <CardContent>
                    {content.text && (
                        <p className="text-sm text-muted-foreground">{content.text}</p>
                    )}
                    {content.items && Array.isArray(content.items) && (
                        <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                            {content.items.map((item: string, i: number) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    )}
                    {content.data && (
                        <pre className="text-xs bg-black/20 p-2 rounded overflow-x-auto">
                            {JSON.stringify(content.data, null, 2)}
                        </pre>
                    )}
                </CardContent>
            )}
        </Card>
    );
}

/**
 * Renders a UI based on the A2UI (Agent-to-UI) protocol.
 *
 * This component consumes a stream of A2UI messages (`surfaceUpdate`, `beginRendering`, etc.)
 * and dynamically renders them using a registry of mapped React components.
 *
 * Also supports simple card-style objects as a fallback for non-protocol payloads.
 *
 * @param props.content - Array of A2UI protocol messages, or a simple card object.
 * @param props.onAction - Callback handler for interactive elements (e.g., buttons).
 * @param props.className - Additional CSS classes.
 */
export default function A2UIRenderer({ content, onAction, className }: A2UIRendererProps) {
    const [components, setComponents] = useState<Map<string, A2UIComponent>>(new Map());
    const [rootId, setRootId] = useState<string | null>(null);
    const [isSimpleContent, setIsSimpleContent] = useState(false);

    useEffect(() => {
        if (!content) return;

        // Check if content is a simple object (not an array of protocol messages)
        if (!Array.isArray(content)) {
            setIsSimpleContent(true);
            return;
        }

        setIsSimpleContent(false);
        const compMap = new Map(components);

        content.forEach(msg => {
            if (msg.surfaceUpdate) {
                msg.surfaceUpdate.components.forEach((c: any) => {
                    compMap.set(c.id, c.component);
                });
            } else if (msg.beginRendering) {
                setRootId(msg.beginRendering.root);
            }
        });

        setComponents(compMap);
    }, [content]);

    const renderComponent = (id: string): React.ReactNode => {
        const compDef = components.get(id);
        if (!compDef) return <div className="text-red-500 text-xs">Missing: {id}</div>;

        // The component object has exactly one key (the type)
        const type = Object.keys(compDef)[0];
        const props = compDef[type];
        const Renderer = ComponentRegistry[type];

        if (!Renderer) return <div className="text-yellow-500 text-xs">Unknown: {type}</div>;

        return (
            <Renderer
                {...props}
                renderId={renderComponent}
                onAction={onAction}
            />
        );
    };

    // Render simple card content as fallback
    if (isSimpleContent) {
        return (
            <div className={cn("a2ui-surface w-full", className)}>
                <SimpleCardRenderer content={content} />
            </div>
        );
    }

    if (!rootId) return <div className="animate-pulse h-32 bg-secondary/20 rounded-lg" />;

    return (
        <div className={cn("a2ui-surface w-full", className)}>
            {renderComponent(rootId)}
        </div>
    );
}
