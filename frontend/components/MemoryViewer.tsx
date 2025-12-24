'use client';

import { useState, useEffect } from 'react';
import { api, MemoryItem } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Brain, Search, Plus, Loader2 } from "lucide-react";

/**
 * MemoryViewer Component
 * 
 * Displays and manages the "Cipher Memory".
 * Allows users to search existing memories and add new ones (Facts, Preferences, Skills).
 * Uses the `api.searchMemory` and `api.addMemory` endpoints.
 */
export default function MemoryViewer() {
    const [memories, setMemories] = useState<MemoryItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [showAdd, setShowAdd] = useState(false);
    const [newContent, setNewContent] = useState('');
    const [newCategory, setNewCategory] = useState('fact');

    const fetchMemories = async () => {
        setLoading(true);
        try {
            const data = await api.searchMemory(searchQuery);
            setMemories(data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMemories();
    }, [searchQuery]);

    const handleAdd = async () => {
        if (!newContent.trim()) return;
        try {
            await api.addMemory(newCategory, { text: newContent });
            setNewContent('');
            setShowAdd(false);
            fetchMemories();
        } catch (e) {
            console.error("Failed to add memory", e);
        }
    };

    return (
        <Card className="glass-card flex flex-col h-full min-h-[400px]">
            <CardHeader className="bg-gradient-to-r from-card to-card/50 border-b border-border/40 pb-4">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-pink-500/10 text-pink-500">
                            <Brain className="h-5 w-5" />
                        </div>
                        <CardTitle className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-pink-500 to-purple-500">
                            Cipher Memory
                        </CardTitle>
                    </div>
                    <button 
                        onClick={() => setShowAdd(!showAdd)}
                        className="p-1.5 hover:bg-white/5 rounded-md transition-colors"
                        title="Add Memory"
                    >
                        <Plus className={`h-5 w-5 ${showAdd ? 'rotate-45' : ''} transition-transform`} />
                    </button>
                </div>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col p-4 gap-4">
                {/* Search / Add Bar */}
                {showAdd ? (
                    <div className="bg-secondary/30 p-3 rounded-lg border border-border/50 space-y-3 animate-in fade-in slide-in-from-top-2">
                        <select 
                            className="w-full bg-background/50 border border-border/50 rounded-md p-2 text-sm focus:ring-1 focus:ring-pink-500"
                            value={newCategory}
                            onChange={(e) => setNewCategory(e.target.value)}
                        >
                            <option value="fact">Fact</option>
                            <option value="preference">Preference</option>
                            <option value="skill_learned">Learned Skill</option>
                        </select>
                        <textarea 
                            className="w-full bg-background/50 border border-border/50 rounded-md p-2 text-sm min-h-[60px] focus:ring-1 focus:ring-pink-500"
                            placeholder="Enter memory content..."
                            value={newContent}
                            onChange={(e) => setNewContent(e.target.value)}
                        />
                        <button 
                            onClick={handleAdd}
                            className="w-full py-1.5 bg-pink-600/80 hover:bg-pink-600 text-white rounded-md text-sm font-medium transition-colors"
                        >
                            Save Memory
                        </button>
                    </div>
                ) : (
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        <input 
                            type="text" 
                            placeholder="Search memories..." 
                            className="w-full pl-9 pr-3 py-2 bg-secondary/30 border border-border/50 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-pink-500/50"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                )}

                {/* List */}
                <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                    {loading && memories.length === 0 ? (
                        <div className="flex justify-center p-4">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : memories.length === 0 ? (
                        <div className="text-center text-muted-foreground text-xs py-8">
                            No memories found.
                        </div>
                    ) : (
                        memories.map((m) => (
                            <div key={m.id} className="group p-3 rounded-lg bg-card/40 hover:bg-card/60 border border-border/30 hover:border-pink-500/30 transition-all">
                                <div className="flex justify-between items-start mb-1">
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                                        m.category === 'fact' ? 'bg-blue-500/10 text-blue-300 border-blue-500/20' :
                                        m.category === 'preference' ? 'bg-orange-500/10 text-orange-300 border-orange-500/20' :
                                        'bg-purple-500/10 text-purple-300 border-purple-500/20'
                                    }`}>
                                        {m.category.toUpperCase()}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground">
                                        {new Date(m.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <div className="text-sm text-foreground/90 font-mono leading-relaxed break-words">
                                    {typeof m.content === 'object' ? JSON.stringify(m.content) : m.content}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
