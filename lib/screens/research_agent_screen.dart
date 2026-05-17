import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../constants/constants.dart';
import '../models/research_models.dart';
import '../providers/app_state_provider.dart';
import '../services/research_service.dart';
import '../widgets/widgets.dart';

class ResearchAgentScreen extends StatefulWidget {
  const ResearchAgentScreen({super.key});

  @override
  State<ResearchAgentScreen> createState() => _ResearchAgentScreenState();
}

class _ResearchAgentScreenState extends State<ResearchAgentScreen> {
  final TextEditingController _topicController = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  bool _isSearching = false;
  String? _errorText;
  List<String> keyFindings = [];
  List<String> _links = [];

  @override
  void dispose() {
    _topicController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _searchTopic() async {
    final topic = _topicController.text.trim();
    if (topic.isEmpty) {
      setState(() => _errorText = 'Please enter a topic to search.');
      return;
    }
    _focusNode.unfocus();

    setState(() {
      _errorText = null;
      _isSearching = true;
      keyFindings = [];
      _links = [];
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final response = await ResearchService.research(
        question: topic,
        appState: appState,
      );

      if (!mounted) return;

      // Build sub-questions from finding section labels + content snippet
      final questions = response.findings.entries.map((e) {
        return '${ResearchResponse.sectionLabel(e.key)}: ${e.value.content.length > 120 ? e.value.content.substring(0, 120).trimRight() + '...' : e.value.content}';
      }).toList();

      setState(() {
        _isSearching = false;
        keyFindings = questions;
        _links = response.allSources;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSearching = false;
        _errorText = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
  // ── Widgets ───────────────────────────────────────────────────────────────

  Widget _buildSearchBar() {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: context.cardShadow,
      ),
      padding: EdgeInsets.all(AppStyles.spacingL),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Dive deeper into any topic',
            style: AppStyles.h3.copyWith(color: context.textPrimary),
          ),
          Text(
            'Get key findings about your topic and research links',
            style: AppStyles.caption,
          ),

          const SizedBox(height: AppStyles.spacingL),
          TextField(
            controller: _topicController,
            focusNode: _focusNode,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _searchTopic(),
            style: AppStyles.bodyMedium.copyWith(color: context.textPrimary),
            decoration: AppStyles.inputDecoration(
              context: context,
              hint: 'What would you like to explore..?',
              suffixIcon: ValueListenableBuilder<TextEditingValue>(
                valueListenable: _topicController,
                builder: (_, value, __) => value.text.isNotEmpty
                    ? IconButton(
                        icon: Icon(
                          Icons.clear,
                          color: context.textSecondary,
                          size: 18,
                        ),
                        onPressed: () {
                          _topicController.clear();
                          setState(() {
                            keyFindings = [];
                            _links = [];
                            _errorText = null;
                          });
                        },
                      )
                    : const SizedBox.shrink(),
              ),
            ),
          ),
          if (_errorText != null) ...[
            const SizedBox(height: AppStyles.spacingS),
            Row(
              children: [
                const Icon(
                  Icons.error_outline,
                  color: AppColors.error,
                  size: 14,
                ),
                const SizedBox(width: 4),
                Expanded(
                  // ← add this
                  child: Text(
                    _errorText!,
                    style: AppStyles.caption.copyWith(color: AppColors.error),
                  ),
                ), // ← close Expanded
              ],
            ),
          ],
          const SizedBox(height: AppStyles.spacingM),
          CustomButton(
            text: _isSearching ? 'Searching…' : 'Search',
            onPressed: _isSearching ? () {} : _searchTopic,
            fullWidth: true,
            buttonType: ButtonType.primary,
            suffixIcon: Icon(Icons.search, size: 18, color: context.cardColor),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppStyles.spacingXL),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: context.cardShadow,
      ),
      child: Column(
        children: [
          Text(
            'Researching topic…',
            style: AppStyles.h3.copyWith(color: context.textPrimary),
          ),
          const SizedBox(height: AppStyles.spacingS),
          Text(
            'For key Findings and research links',
            style: AppStyles.caption,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppStyles.spacingXL),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: context.cardShadow,
      ),
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: AppColors.primaryColor.withOpacity(0.08),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.auto_awesome_outlined,
              color: AppColors.primaryColor,
              size: 32,
            ),
          ),
          const SizedBox(height: AppStyles.spacingL),
          Text(
            'Ready to explore',
            style: AppStyles.h3.copyWith(color: context.textPrimary),
          ),
          const SizedBox(height: AppStyles.spacingS),
          Text(
            'Enter a topic above and press Search to generate related topics and curated research links.',
            style: AppStyles.caption,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildKeyFindingsCard() {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: context.cardShadow,
      ),
      padding: const EdgeInsets.all(AppStyles.spacingL),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Icon(
                Icons.vpn_key_outlined,
                color: AppColors.primaryColor,
                size: 30,
              ),
              const SizedBox(width: AppStyles.spacingM),
              Text(
                'key Findings',
                style: AppStyles.h3.copyWith(color: context.textPrimary),
              ),
            ],
          ),
          const SizedBox(height: AppStyles.spacingL),
          Divider(color: AppColors.primaryColor, height: 1, endIndent: 20),
          const SizedBox(height: AppStyles.spacingM),

          // Questions
          ...keyFindings.asMap().entries.map((entry) {
            return Padding(
              padding: const EdgeInsets.only(bottom: AppStyles.spacingM),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: AppColors.primaryColor,
                      borderRadius: BorderRadius.circular(AppStyles.radiusS),
                    ),
                    child: Center(
                      child: Text(
                        '${entry.key + 1}',
                        style: AppStyles.caption.copyWith(
                          fontWeight: AppFonts.bold,
                          color: context.cardColor,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppStyles.spacingM),
                  Expanded(
                    child: Builder(
                      builder: (_) {
                        final parts = entry.value.split(': ');
                        final label = parts.first;
                        final rest = parts.length > 1
                            ? parts.sublist(1).join(': ')
                            : '';
                        return RichText(
                          text: TextSpan(
                            style: AppStyles.bodyMedium.copyWith(
                              color: context.textPrimary,
                            ),
                            children: [
                              TextSpan(
                                text: '$label: ',
                                style: AppStyles.bodyMedium.copyWith(
                                  color: context.textPrimary,
                                  fontWeight: AppFonts.bold,
                                ),
                              ),
                              TextSpan(text: rest),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildLinksCard() {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: context.cardShadow,
      ),
      padding: EdgeInsets.all(AppStyles.spacingM),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(
                Icons.travel_explore_rounded,
                color: AppColors.primaryColor,
                size: 30,
              ),
              const SizedBox(width: AppStyles.spacingM),
              Text(
                'Research Links',
                style: AppStyles.h3.copyWith(color: context.textPrimary),
              ),
            ],
          ),
          const SizedBox(height: AppStyles.spacingM),
          Divider(color: AppColors.primaryColor, height: 1),
          const SizedBox(height: AppStyles.spacingM),

          // Links
          ..._links.map((link) {
            final uri = Uri.parse(link);
            final domain = uri.host
                .replaceFirst('www.', '')
                .replaceFirst('scholar.', '');

            return Padding(
              padding: const EdgeInsets.only(bottom: AppStyles.spacingM),
              child: InkWell(
                onTap: () => _launchUrl(link),
                borderRadius: BorderRadius.circular(AppStyles.radiusM),
                child: Container(
                  padding: const EdgeInsets.all(AppStyles.spacingM),
                  decoration: BoxDecoration(
                    color: AppColors.primaryColor.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(AppStyles.radiusM),
                    border: Border.all(
                      color: AppColors.primaryColor.withOpacity(0.15),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: AppColors.primaryColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(
                            AppStyles.radiusS,
                          ),
                        ),
                        child: const Icon(
                          Icons.language_rounded,
                          color: AppColors.primaryColor,
                          size: 16,
                        ),
                      ),
                      const SizedBox(width: AppStyles.spacingM),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              domain,
                              style: AppStyles.bodyMedium.copyWith(
                                color: AppColors.primaryColor,
                                fontWeight: AppFonts.semiBold,
                              ),
                            ),
                            Text(
                              link,
                              style: AppStyles.caption.copyWith(
                                color: context.textSecondary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      Icon(
                        Icons.open_in_new_rounded,
                        size: 16,
                        color: context.textSecondary,
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: CustomAppBar(title: 'Research Agent', showBackButton: true),
      body: LoadingOverlay(
        isLoading: _isSearching,
        child: SingleChildScrollView(
          padding: EdgeInsets.all(AppStyles.spacingL),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Search card
              _buildSearchBar(),
              const SizedBox(height: AppStyles.spacingL),

              // Results area
              if (_isSearching)
                _buildLoadingState()
              else if (keyFindings.isEmpty && _links.isEmpty)
                _buildEmptyState()
              else ...[
                _buildKeyFindingsCard(),
                const SizedBox(height: AppStyles.spacingL),
                _buildLinksCard(),
              ],

              const SizedBox(height: AppStyles.spacingXXL),
            ],
          ),
        ),
      ),
    );
  }
}
