'use client';

import { useState, useEffect } from 'react';
import { api, SkillItem } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Wrench, Power, Loader2 } from "lucide-react";

/**
 * SkillsRegistry Component
 * 
 * Visualizes the registered agents/skills in the system.
 * Allows toggling skills on/off via the `api.toggleSkill` endpoint.
 * Provides a UI for managing capability availability.
 */
export default function SkillsRegistry() {
    const [skills, setSkills] = useState<SkillItem[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchSkills = async () => {
        setLoading(true);
        try {
            const data = await api.getSkills();
            setSkills(data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSkills();
    }, []);

    const handleToggle = async (id: string, current: boolean) => {
        // Optimistic update
        setSkills(prev => prev.map(s => s.id === id ? { ...s, enabled: !current } : s));
        try {
            await api.toggleSkill(id, !current);
        } catch (e) {
            // Revert on failure
            setSkills(prev => prev.map(s => s.id === id ? { ...s, enabled: current } : s));
            console.error(e);
        }
    };

    return (
        <Card className="glass-card flex flex-col h-full min-h-[400px]">
            <CardHeader className="bg-gradient-to-r from-card to-card/50 border-b border-border/40 pb-4">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-orange-500/10 text-orange-500">
                            <Wrench className="h-5 w-5" />
                        </div>
                        <CardTitle className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-orange-500 to-amber-500">
                            Agent Skills
                        </CardTitle>
                    </div>
                     <span className="text-xs text-muted-foreground">{skills.length} Loaded</span>
                </div>
            </CardHeader>

            <CardContent className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                {loading && skills.length === 0 ? (
                    <div className="flex justify-center p-4">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : skills.length === 0 ? (
                    <div className="text-center text-muted-foreground text-xs py-8">
                        No skills registered in the registry.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3">
                        {skills.map((skill) => (
                            <div key={skill.id} className={`p-4 rounded-xl border transition-all ${
                                skill.enabled 
                                ? 'bg-card/60 border-orange-500/20 shadow-sm' 
                                : 'bg-secondary/10 border-border/30 opacity-60'
                            }`}>
                                <div className="flex justify-between items-start mb-2">
                                    <h4 className="font-semibold text-sm text-foreground">{skill.name}</h4>
                                    <button 
                                        onClick={() => handleToggle(skill.id, skill.enabled)}
                                        className={`p-1.5 rounded-full transition-colors ${
                                            skill.enabled ? 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30' : 'bg-white/5 text-muted-foreground hover:bg-white/10'
                                        }`}
                                    >
                                        <Power className="h-4 w-4" />
                                    </button>
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {skill.description}
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
