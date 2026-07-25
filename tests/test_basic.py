#!/usr/bin/env python3
"""
VAgent Test Suite

Basic tests to verify the VAgent system is working correctly.
"""

import asyncio
import sys
import tempfile
import json
from pathlib import Path

# Add vagent to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vagent.core import VAgentOrchestrator
from vagent.models import ResearchTask, Trend, VideoContent
from vagent.utils import load_config, validate_config


async def test_config_loading():
    """Test configuration loading and validation."""
    print("Testing configuration loading...")
    
    try:
        config = load_config()
        assert validate_config(config), "Configuration validation failed"
        print("✅ Configuration loading and validation passed")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    print("Testing orchestrator initialization...")
    
    try:
        orchestrator = VAgentOrchestrator()
        assert orchestrator is not None, "Orchestrator initialization failed"
        print("✅ Orchestrator initialization passed")
        return True
    except Exception as e:
        print(f"❌ Orchestrator initialization test failed: {e}")
        return False


async def test_research_tasks():
    """Test research task creation and basic functionality."""
    print("Testing research tasks...")
    
    try:
        # Create test research tasks
        tasks = [
            ResearchTask(
                id="test_tech",
                category="technology",
                query="AI trends 2024",
                max_websites=10,
                priority=2
            ),
            ResearchTask(
                id="test_business", 
                category="business",
                query="startup innovation",
                max_websites=10,
                priority=1
            )
        ]
        
        assert len(tasks) == 2, "Task creation failed"
        assert tasks[0].category == "technology", "Task properties incorrect"
        
        print("✅ Research tasks test passed")
        return True
    except Exception as e:
        print(f"❌ Research tasks test failed: {e}")
        return False


async def test_trend_analysis():
    """Test trend analysis functionality."""
    print("Testing trend analysis...")
    
    try:
        orchestrator = VAgentOrchestrator()
        
        # Create mock research results
        from vagent.models import ResearchResult
        mock_results = [
            ResearchResult(
                url="https://example.com/ai-trends",
                title="AI Trends 2024",
                content="Artificial intelligence is transforming industries...",
                category="technology",
                relevance_score=0.8
            ),
            ResearchResult(
                url="https://example.com/startup-innovation",
                title="Startup Innovation",
                content="New startups are disrupting traditional markets...",
                category="business",
                relevance_score=0.7
            )
        ]
        
        # Test trend analysis
        trend_analysis = await orchestrator.trend_analyzer.analyze_trends(
            mock_results, 
            top_n=5
        )
        
        assert trend_analysis is not None, "Trend analysis failed"
        assert len(trend_analysis.trends) > 0, "No trends found"
        
        print("✅ Trend analysis test passed")
        return True
    except Exception as e:
        print(f"❌ Trend analysis test failed: {e}")
        return False


async def test_content_strategy():
    """Test content strategy functionality."""
    print("Testing content strategy...")
    
    try:
        orchestrator = VAgentOrchestrator()
        
        # Create mock trend analysis
        from vagent.models import TrendAnalysis, Trend
        mock_trends = [
            Trend(
                topic="AI in Healthcare",
                category="technology",
                trend_score=0.9,
                growth_rate=0.8,
                search_volume=10000,
                engagement_score=0.7
            ),
            Trend(
                topic="Sustainable Technology",
                category="technology", 
                trend_score=0.8,
                growth_rate=0.6,
                search_volume=8000,
                engagement_score=0.6
            )
        ]
        
        mock_analysis = TrendAnalysis(trends=mock_trends)
        
        # Test content strategy
        selected_topics = await orchestrator.content_strategist.select_topics(
            mock_analysis,
            videos_per_topic=2
        )
        
        assert selected_topics is not None, "Content strategy failed"
        assert len(selected_topics) > 0, "No topics selected"
        
        print("✅ Content strategy test passed")
        return True
    except Exception as e:
        print(f"❌ Content strategy test failed: {e}")
        return False


async def test_video_production():
    """Test video production functionality."""
    print("Testing video production...")
    
    try:
        orchestrator = VAgentOrchestrator()
        
        # Create mock selected topics
        from vagent.models import TopicAssessment
        mock_topics = [
            {
                'topic': 'AI in Healthcare',
                'category': 'technology',
                'assessment': TopicAssessment(
                    topic='AI in Healthcare',
                    category='technology',
                    attention_potential=0.9,
                    competition_level=0.3,
                    audience_size=50000,
                    content_gap_score=0.8,
                    monetization_potential=0.7,
                    viral_probability=0.6,
                    key_points=['AI in healthcare', 'Medical applications'],
                    target_audience=['Healthcare professionals', 'Patients'],
                    content_hooks=['Revolutionary AI in healthcare', 'Medical breakthrough']
                )
            }
        ]
        
        # Test video production
        video_contents = await orchestrator.video_producer.create_videos(
            mock_topics,
            videos_per_topic=2
        )
        
        assert video_contents is not None, "Video production failed"
        assert len(video_contents) > 0, "No videos created"
        
        # Check video properties
        for video in video_contents:
            assert video.title is not None, "Video title missing"
            assert video.description is not None, "Video description missing"
            assert video.duration > 0, "Video duration invalid"
        
        print("✅ Video production test passed")
        return True
    except Exception as e:
        print(f"❌ Video production test failed: {e}")
        return False


async def test_publishing():
    """Test publishing functionality."""
    print("Testing publishing...")
    
    try:
        orchestrator = VAgentOrchestrator()
        
        # Create mock video contents
        from vagent.models import VideoContent, VideoFormat, Platform
        mock_videos = [
            VideoContent(
                id="test_video_1",
                topic="AI in Healthcare",
                title="AI in Healthcare Explained",
                description="Understanding AI applications in healthcare",
                format=VideoFormat.MEDIUM_FORM,
                target_platforms=[Platform.YOUTUBE],
                duration=180,
                assessment=None
            )
        ]
        
        # Test publishing
        publishing_results = await orchestrator.publisher.publish_videos(
            mock_videos,
            ["youtube"]
        )
        
        assert publishing_results is not None, "Publishing failed"
        assert len(publishing_results) > 0, "No publishing results"
        
        print("✅ Publishing test passed")
        return True
    except Exception as e:
        print(f"❌ Publishing test failed: {e}")
        return False


async def test_full_pipeline():
    """Test the complete pipeline with minimal data."""
    print("Testing full pipeline...")
    
    try:
        orchestrator = VAgentOrchestrator()
        
        # Run minimal pipeline
        results = await orchestrator.run_full_pipeline(
            research_websites=10,    # Very small for testing
            top_trends=5,           # Small number
            videos_per_topic=1,     # Single video per topic
            target_platforms=["youtube"]  # Single platform
        )
        
        assert results is not None, "Full pipeline failed"
        assert 'research_results' in results, "Missing research results"
        assert 'trend_analysis' in results, "Missing trend analysis"
        assert 'selected_topics' in results, "Missing selected topics"
        assert 'video_contents' in results, "Missing video contents"
        assert 'publishing_results' in results, "Missing publishing results"
        
        print("✅ Full pipeline test passed")
        return True
    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        return False


async def test_file_operations():
    """Test file operations and result saving."""
    print("Testing file operations...")
    
    try:
        orchestrator = VAgentOrchestrator()
        
        # Create test results
        test_results = {
            'test_phase': 'file_operations_test',
            'timestamp': str(asyncio.get_event_loop().time()),
            'data': {'test': 'data'}
        }
        
        # Test saving results
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_results.json"
            saved_file = orchestrator.save_results(test_results, str(output_file))
            
            assert saved_file.exists(), "Results file not created"
            
            # Test loading results
            with open(saved_file, 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == test_results, "Results data mismatch"
        
        print("✅ File operations test passed")
        return True
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("🧪 VAgent Test Suite")
    print("=" * 40)
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Orchestrator Initialization", test_orchestrator_initialization),
        ("Research Tasks", test_research_tasks),
        ("Trend Analysis", test_trend_analysis),
        ("Content Strategy", test_content_strategy),
        ("Video Production", test_video_production),
        ("Publishing", test_publishing),
        ("Full Pipeline", test_full_pipeline),
        ("File Operations", test_file_operations),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 40)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed/len(tests)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! VAgent is ready to use.")
        return True
    else:
        print(f"\n⚠️  {failed} tests failed. Please check the errors above.")
        return False


async def main():
    """Main test function."""
    success = await run_all_tests()
    
    if success:
        print("\n🚀 Next steps:")
        print("1. Run the comprehensive example: python vagent/examples/comprehensive_example.py")
        print("2. Run the main pipeline: python vagent/main.py --websites 100 --trends 10")
        print("3. Check the generated results in the vagent_results/ directory")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check that all dependencies are installed: pip install -r vagent/requirements.txt")
        print("2. Verify API keys are set in environment variables")
        print("3. Check Python version (requires 3.8+)")
        print("4. Run individual tests to identify specific issues")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)