from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .service import TextAnalysisService
from .types import AnalysisState, AnalysisType


def create_analysis_workflow() -> StateGraph:
    workflow = StateGraph(AnalysisState)

    async def analyze_weak_spots_node(state: AnalysisState) -> AnalysisState:
        if AnalysisType.WEAK_SPOTS in state.analysis_types:
            service = TextAnalysisService()
            weak_spots, recommendations = await service.analyze_weak_spots(state.original_text, state.language)
            state.weak_spots = weak_spots
            state.metadata['weak_spots_recommendations'] = recommendations
        return state

    async def combined_processing_node(state: AnalysisState) -> AnalysisState:
        processing_types = [t for t in state.analysis_types if t != AnalysisType.WEAK_SPOTS]
        if processing_types:
            service = TextAnalysisService()
            result = await service.process_text_combined(
                state.original_text, processing_types, state.style, state.language
            )
            state.current_text = result.get('processed_text', state.original_text)
            state.speech_time_minutes = result.get('speech_time_original')
            state.word_count = result.get('word_count_original', 0)
            state.final_speech_time_minutes = result.get('final_speech_time')
            state.final_word_count = result.get('word_count_final', 0)
            state.processing_steps.append(
                {
                    'step_name': 'Комплексная обработка',
                    'input_text': state.original_text,
                    'output_text': state.current_text,
                    'changes_made': result.get('changes_summary', []),
                    'metadata': result.get('processing_details', {}),
                }
            )
        return state

    workflow.add_node('analyze_weak_spots', analyze_weak_spots_node)
    workflow.add_node('combined_processing', combined_processing_node)

    workflow.set_entry_point('analyze_weak_spots')
    workflow.add_edge('analyze_weak_spots', 'combined_processing')
    workflow.add_edge('combined_processing', END)

    return workflow


analysis_workflow = create_analysis_workflow()
memory = MemorySaver()
app_graph = analysis_workflow.compile(checkpointer=memory)
